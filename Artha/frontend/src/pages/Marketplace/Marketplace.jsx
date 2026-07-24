import { useState, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import loanService from '../../services/loanService';
import { ChevronRight, PlusCircle, Search, ShieldCheck, TrendingUp } from 'lucide-react';
import '../../styles/global.css';
import './Marketplace.css';

const inferCategory = (purpose = '') => {
    const p = purpose.toLowerCase();
    if (p.includes('business') || p.includes('shop') || p.includes('inventory') || p.includes('startup')) return 'Business';
    if (p.includes('agricultur') || p.includes('farm') || p.includes('seed') || p.includes('fertilizer')) return 'Agriculture';
    if (p.includes('student') || p.includes('fee') || p.includes('tuition') || p.includes('education')) return 'Education';
    return 'Personal';
};

const getRiskScore = (score) => {
    if (!score) return 'N/A';
    if (score >= 750) return 'A+';
    if (score >= 700) return 'A';
    if (score >= 650) return 'B';
    if (score >= 600) return 'C';
    return 'D';
};

const Marketplace = () => {
    const { user, bankLinked, refreshUser } = useAuth();
    const navigate = useNavigate();
    const [searchTerm, setSearchTerm] = useState('');
    const [activeCategory, setActiveCategory] = useState('All');
    const [loans, setLoans] = useState([]);
    const [loading, setLoading] = useState(true);

    const userRole = user?.activeRole && user.activeRole !== 'none' ? user.activeRole : user?.preferredRole;
    const isLender = userRole === 'lender';
    const linkedBank = bankLinked || Boolean(user?.bankAccountNumber);
    const categories = ['All', 'Agriculture', 'Business', 'Education', 'Personal'];

    useEffect(() => {
        const fetchLoans = async () => {
            try {
                const data = await loanService.getMarketplaceListings();
                const mappedLoans = data.map((loan) => ({
                    id: loan.loan_id,
                    borrower: loan.borrower_name,
                    purpose: loan.purpose,
                    category: inferCategory(loan.purpose),
                    amount: loan.amount,
                    lenderMaxAmount: loan.lender_max_amount || Math.floor(loan.amount * 0.1),
                    tenure: loan.tenure_months,
                    interest: loan.interest_rate,
                    funded: 0,
                    riskScore: getRiskScore(loan.credit_score),
                    rawScore: loan.credit_score,
                }));
                setLoans(mappedLoans);
            } catch (error) {
                console.error('Failed to fetch loans', error);
            } finally {
                setLoading(false);
            }
        };

        fetchLoans();
        const interval = setInterval(() => {
            if (!document.hidden) fetchLoans();
        }, 60000);
        return () => clearInterval(interval);
    }, []);

    const filteredLoans = useMemo(() => {
        return loans.filter((loan) => {
            const query = searchTerm.toLowerCase();
            const matchesSearch = loan.borrower.toLowerCase().includes(query) ||
                loan.purpose.toLowerCase().includes(query);
            const matchesCategory = activeCategory === 'All' || loan.category === activeCategory;
            return matchesSearch && matchesCategory;
        });
    }, [searchTerm, activeCategory, loans]);

    const handleRequestLoan = () => {
        if (!user) {
            navigate('/login');
            return;
        }
        if (!linkedBank) {
            navigate('/bank-connection-demo');
            return;
        }
        if (isLender) {
            alert('This account was created for lending. Please use a borrower account to request a loan.');
            return;
        }
        if (user.kycStatus !== 'verified') {
            alert('Please complete KYC to request a loan.');
            navigate('/kyc');
            return;
        }
        navigate('/request-loan');
    };

    const handleFund = async (loan) => {
        if (!user) {
            navigate('/login');
            return;
        }
        const latestUser = user.bankAccountNumber ? user : await refreshUser().catch(() => null);
        const latestLinkedBank = Boolean(latestUser?.bankLinked || latestUser?.bankAccountNumber || linkedBank);
        if (!latestLinkedBank || !latestUser?.bankAccountNumber) {
            navigate('/bank-connection-demo');
            return;
        }
        if (!isLender) {
            alert('This account was created for borrowing. Please use a lender account to fund loans.');
            return;
        }
        if (user.kycStatus !== 'verified') {
            alert('Please complete KYC to invest.');
            navigate('/kyc');
            return;
        }

        const LENDING_LIMIT = 500000;
        const fundingAmount = loan.lenderMaxAmount || Math.floor(loan.amount * 0.1);
        const totalLended = latestUser.totalLended || 0;
        if (totalLended + fundingAmount > LENDING_LIMIT) {
            alert(`Investment failed. Your total lending limit is NPR ${LENDING_LIMIT.toLocaleString()}. You have already lended NPR ${totalLended.toLocaleString()}.`);
            return;
        }

        navigate('/payment', { state: { loan: { ...loan, fundingAmount } } });
    };

    return (
        <div className="container marketplace-container mt-8 mb-12 animate-fade">
            <div className="marketplace-header flex justify-between items-end mb-10">
                <div>
                    <span className="hero-badge mb-2">
                        <TrendingUp size={14} /> LIVE OPPORTUNITIES
                    </span>
                    <h1 className="text-4xl font-bold">{isLender ? 'Lending Marketplace' : 'Borrowing Hub'}</h1>
                    <p className="text-muted text-lg">
                        {isLender
                            ? 'Choose direct loans from verified borrowers.'
                            : 'Prepare your loan request and track borrower-ready opportunities.'}
                    </p>
                </div>
                {!isLender && (
                    <button onClick={handleRequestLoan} className="btn btn-primary px-8 py-3">
                        <PlusCircle size={18} style={{ marginRight: '0.6rem' }} /> Request Loan
                    </button>
                )}
            </div>

            <div className="marketplace-filters mb-10">
                <div className="search-container shadow-sm focus-within:shadow-md transition-shadow">
                    <Search className="search-icon" size={18} />
                    <input
                        type="text"
                        placeholder="Search products, borrowers, or purpose..."
                        className="search-input"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
                <div className="filter-group">
                    {categories.map((cat) => (
                        <button
                            key={cat}
                            className={`filter-btn ${activeCategory === cat ? 'active' : ''}`}
                            onClick={() => setActiveCategory(cat)}
                        >
                            {cat}
                        </button>
                    ))}
                </div>
            </div>

            {loading ? (
                <div className="text-center p-12"><div className="spinner"></div> Loading Marketplace...</div>
            ) : filteredLoans.length > 0 ? (
                <div className="loans-grid grid grid-3 gap-8">
                    {filteredLoans.map((loan, index) => (
                        <div key={loan.id} className="loan-card card glass hover:shadow-xl transition-all" style={{ animationDelay: `${index * 0.1}s` }}>
                            <div className="loan-header flex justify-between items-start mb-6">
                                <div className="borrower-info flex gap-4">
                                    <div className="avatar-placeholder ring-2 ring-primary ring-offset-2 ring-offset-white">{loan.borrower[0]}</div>
                                    <div>
                                        <h4 className="text-lg font-bold">{loan.borrower}</h4>
                                        <div className="flex items-center gap-1 text-xs font-semibold text-success uppercase">
                                            <ShieldCheck size={12} /> KYC Verified
                                        </div>
                                    </div>
                                </div>
                                {loan.riskScore !== 'N/A' && (
                                    <span className={`risk-badge risk-${loan.riskScore.replace('+', 'plus')}`}>Risk {loan.riskScore}</span>
                                )}
                            </div>

                            <div className="loan-details p-5 rounded-2xl bg-slate-50/50 mb-8 border border-slate-100">
                                <p className="purpose font-medium text-slate-700 leading-relaxed mb-6">"{loan.purpose}"</p>

                                <div className="stats-row flex flex-col gap-4">
                                    <div className="detail-row flex justify-between items-center">
                                        <span className="text-muted text-sm font-medium">Loan Amount</span>
                                        <span className="text-lg font-black text-slate-800">NPR {loan.amount.toLocaleString()}</span>
                                    </div>

                                    <div className="progress-container">
                                        <div className="flex justify-between text-xs font-bold mb-2">
                                            <span className="text-primary">{loan.funded}% Funded</span>
                                            <span className="text-muted">Target: NPR {loan.amount.toLocaleString()}</span>
                                        </div>
                                        <div className="progress-bar-bg h-2 rounded-full bg-slate-200 overflow-hidden">
                                            <div className="progress-fill h-full bg-primary" style={{ width: `${loan.funded}%` }}></div>
                                        </div>
                                    </div>

                                    <div className="flex justify-between pt-4 border-t border-slate-100">
                                        <div className="flex flex-col">
                                            <span className="text-xs text-muted font-bold uppercase tracking-wider">Returns</span>
                                            <span className="text-success font-bold">{loan.interest}% p.a.</span>
                                        </div>
                                        <div className="flex flex-col text-right">
                                            <span className="text-xs text-muted font-bold uppercase tracking-wider">Tenure</span>
                                            <span className="font-bold">{loan.tenure} Mo.</span>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <button onClick={() => handleFund(loan)} className="btn btn-primary w-100 py-4 font-bold text-md shadow-lg shadow-blue-500/20" style={{ gap: '0.6rem' }}>
                                Fund NPR {(loan.lenderMaxAmount || Math.floor(loan.amount * 0.1)).toLocaleString()} <ChevronRight size={20} />
                            </button>
                        </div>
                    ))}
                </div>
            ) : (
                <div className="text-center mt-8 p-16 card glass animate-fade">
                    <Search size={64} className="text-slate-300 mb-6 mx-auto" />
                    <h2 className="mb-2 text-2xl font-bold">No products found</h2>
                    <p className="text-muted">Try adjusting your filters or search term to discover more opportunities.</p>
                </div>
            )}
        </div>
    );
};

export default Marketplace;
