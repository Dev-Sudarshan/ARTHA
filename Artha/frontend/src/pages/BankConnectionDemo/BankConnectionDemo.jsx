import { useMemo, useState } from 'react';
import { AlertCircle, Building2, CheckCircle2, CreditCard, LockKeyhole, Phone, RefreshCw, Search, ShieldCheck } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import './BankConnectionDemo.css';

const demoBanks = [
    { id: 'nepal-bank', name: 'Nepal Bank Limited', shortName: 'NBL', balance: 82400, accent: '#0F4C5C' },
    { id: 'rastriya-banijya', name: 'Rastriya Banijya Bank', shortName: 'RBB', balance: 105300, accent: '#1F8A70' },
    { id: 'nabil', name: 'Nabil Bank', shortName: 'Nabil', balance: 126500, accent: '#C28B2C' },
    { id: 'himalayan', name: 'Himalayan Bank', shortName: 'HBL', balance: 73200, accent: '#2563EB' },
    { id: 'standard-chartered', name: 'Standard Chartered Bank Nepal', shortName: 'SCB', balance: 146700, accent: '#0F766E' },
    { id: 'nepal-investment', name: 'Nepal Investment Bank', shortName: 'NIBL', balance: 94300, accent: '#7C3AED' },
    { id: 'bank-of-kathmandu', name: 'Bank of Kathmandu', shortName: 'BOK', balance: 61300, accent: '#D97706' },
    { id: 'everest', name: 'Everest Bank', shortName: 'EBL', balance: 118900, accent: '#DC2626' },
    { id: 'kumari', name: 'Kumari Bank', shortName: 'Kumari', balance: 58750, accent: '#0F74BC' },
    { id: 'machhapuchchhre', name: 'Machhapuchchhre Bank', shortName: 'MBL', balance: 88400, accent: '#0284C7' },
    { id: 'siddhartha', name: 'Siddhartha Bank', shortName: 'SBL', balance: 97500, accent: '#0891B2' },
    { id: 'lumbini', name: 'Lumbini Bank', shortName: 'Lumbini', balance: 54200, accent: '#059669' },
    { id: 'global-ime', name: 'Global IME Bank', shortName: 'Global IME', balance: 138200, accent: '#B91C1C' },
    { id: 'nic-asia', name: 'NIC Asia Bank', shortName: 'NIC Asia', balance: 113600, accent: '#EA580C' },
    { id: 'prabhu', name: 'Prabhu Bank', shortName: 'Prabhu', balance: 69400, accent: '#9333EA' },
    { id: 'shree-investment', name: 'Shree Investment and Finance', shortName: 'Shree', balance: 45800, accent: '#4B5563' },
    { id: 'janata', name: 'Janata Bank', shortName: 'Janata', balance: 76800, accent: '#16A34A' },
    { id: 'citizens', name: 'Citizens Bank International', shortName: 'Citizens', balance: 126500, accent: '#52C69A' },
    { id: 'adbl', name: 'Agricultural Development Bank', shortName: 'ADBL', balance: 82400, accent: '#1F8A70' },
    { id: 'nepal-sbi', name: 'Nepal SBI Bank', shortName: 'SBI', balance: 109700, accent: '#1D4ED8' }
];

const connectionStates = {
    idle: {
        label: 'Choose bank account',
        detail: 'Select a bank and enter demo online banking details.',
        tone: 'neutral',
        icon: Building2
    },
    connecting: {
        label: 'Connecting',
        detail: 'Creating a read-only demo session and checking account access.',
        tone: 'pending',
        icon: RefreshCw
    },
    connected: {
        label: 'Bank account linked',
        detail: 'Balance is available for demo lending and borrower disbursement flows.',
        tone: 'success',
        icon: CheckCircle2
    },
    failed: {
        label: 'Connection failed',
        detail: 'The simulated bank provider could not verify these demo credentials.',
        tone: 'error',
        icon: AlertCircle
    }
};

const formatNpr = (amount) => `NPR ${amount.toLocaleString()}`;

const buildLinkedAccount = (bank, mobileNumber) => ({
    institution: bank.name,
    accountType: 'Savings',
    accountNumber: `XXXX-${mobileNumber.slice(-4) || '2048'}`,
    availableBalance: bank.balance,
    monthlyInflow: Math.round(bank.balance * 0.56),
    borrowerDisbursement: 'Loan disbursement will be deposited to this linked account.',
    lenderDebit: 'Lender funding will be deducted from this linked account.'
});

const BankConnectionDemo = () => {
    const { markBankLinked } = useAuth();
    const [status, setStatus] = useState('idle');
    const [selectedBankId, setSelectedBankId] = useState(demoBanks[0].id);
    const [bankSearch, setBankSearch] = useState('');
    const [credentials, setCredentials] = useState({ mobileNumber: '', password: '' });
    const [linkedAccount, setLinkedAccount] = useState(null);

    const activeState = connectionStates[status];
    const StatusIcon = activeState.icon;
    const selectedBank = demoBanks.find((bank) => bank.id === selectedBankId) || demoBanks[0];

    const filteredBanks = useMemo(() => {
        const query = bankSearch.trim().toLowerCase();
        if (!query) return demoBanks.slice(0, 6);
        return demoBanks.filter((bank) =>
            bank.name.toLowerCase().includes(query) ||
            bank.shortName.toLowerCase().includes(query)
        );
    }, [bankSearch]);

    const handleCredentialChange = (event) => {
        setCredentials({ ...credentials, [event.target.name]: event.target.value });
    };

    const handleConnect = (event) => {
        event.preventDefault();
        setStatus('connecting');
        window.setTimeout(() => {
            setLinkedAccount(buildLinkedAccount(selectedBank, credentials.mobileNumber));
            markBankLinked();
            setStatus('connected');
        }, 1100);
    };

    const handleBankSelect = (bank) => {
        setSelectedBankId(bank.id);
        setBankSearch(bank.name);
    };

    return (
        <div className="container bank-demo-page mt-8 mb-16 animate-fade">
            <div className="demo-header">
                <span className="hero-badge">
                    <ShieldCheck size={14} /> Demo Only
                </span>
                <h1>Link Bank Account</h1>
                <p>Soft-coded mock flow for choosing a bank, entering online banking credentials, and showing the account balance.</p>
            </div>

            <div className="bank-demo-layout">
                <section className="bank-demo-panel">
                    <div className={`bank-status-card ${activeState.tone}`}>
                        <div className="bank-status-icon">
                            <StatusIcon size={28} className={status === 'connecting' ? 'spin' : ''} />
                        </div>
                        <div>
                            <p className="status-eyebrow">Connection status</p>
                            <h2>{activeState.label}</h2>
                            <p>{activeState.detail}</p>
                        </div>
                    </div>

                    <div className="bank-search-box">
                        <label>
                            <span>Search Bank</span>
                            <div className="bank-input-wrap">
                                <Search size={18} />
                                <input
                                    value={bankSearch}
                                    onChange={(event) => setBankSearch(event.target.value)}
                                    placeholder="Search Nepal Bank, Nabil, SBI..."
                                    disabled={status === 'connecting'}
                                />
                            </div>
                        </label>
                        <div className="bank-suggestions">
                            {filteredBanks.map((bank) => (
                                <button
                                    className={`bank-option ${bank.id === selectedBankId ? 'active' : ''}`}
                                    key={bank.id}
                                    onClick={() => handleBankSelect(bank)}
                                    type="button"
                                    disabled={status === 'connecting'}
                                >
                                    <span className="bank-logo-mark" style={{ borderColor: bank.accent, color: bank.accent }}>
                                        {bank.shortName.slice(0, 2)}
                                    </span>
                                    <span>
                                        <strong>{bank.shortName}</strong>
                                        <small>{bank.name}</small>
                                    </span>
                                </button>
                            ))}
                        </div>
                    </div>

                    <form className="bank-login-form" onSubmit={handleConnect}>
                        <label>
                            <span>Mobile Number</span>
                            <div className="bank-input-wrap">
                                <Phone size={18} />
                                <input
                                    name="mobileNumber"
                                    type="tel"
                                    value={credentials.mobileNumber}
                                    onChange={handleCredentialChange}
                                    placeholder="98XXXXXXXX"
                                    minLength="10"
                                    required
                                />
                            </div>
                        </label>
                        <label>
                            <span>Online Banking Password</span>
                            <div className="bank-input-wrap">
                                <LockKeyhole size={18} />
                                <input
                                    name="password"
                                    type="password"
                                    value={credentials.password}
                                    onChange={handleCredentialChange}
                                    placeholder="Demo password"
                                    minLength="4"
                                    required
                                />
                            </div>
                        </label>

                        <div className="bank-actions">
                            <button className="btn btn-primary" type="submit" disabled={status === 'connecting'}>
                                {status === 'connecting' ? <RefreshCw size={18} className="spin" /> : <CreditCard size={18} />}
                                {status === 'connected' ? 'Relink Bank Account' : 'Link Bank Account'}
                            </button>
                        </div>
                    </form>
                </section>

                <section className="bank-summary-panel">
                    <div className="summary-heading">
                        <h2>Read-only Summary</h2>
                        <span className={`summary-badge ${status === 'connected' ? 'ready' : ''}`}>
                            {status === 'connected' ? 'Available' : 'Waiting'}
                        </span>
                    </div>

                    {status === 'connected' ? (
                        <>
                            <div className="summary-grid">
                                <div className="summary-item">
                                    <span>Institution</span>
                                    <strong>{linkedAccount.institution}</strong>
                                </div>
                                <div className="summary-item">
                                    <span>Account</span>
                                    <strong>{linkedAccount.accountNumber}</strong>
                                </div>
                                <div className="summary-item balance">
                                    <span>Available Balance</span>
                                    <strong>{formatNpr(linkedAccount.availableBalance)}</strong>
                                </div>
                                <div className="summary-item">
                                    <span>Monthly Inflow</span>
                                    <strong>{formatNpr(linkedAccount.monthlyInflow)}</strong>
                                </div>
                            </div>
                            <div className="money-flow-list">
                                <p><CheckCircle2 size={16} /> {linkedAccount.borrowerDisbursement}</p>
                                <p><CheckCircle2 size={16} /> {linkedAccount.lenderDebit}</p>
                            </div>
                            <div className="bank-note success">
                                This is demo-only. Later your friend can replace this mock account object with backend NCHL/SBI or wallet data.
                            </div>
                        </>
                    ) : (
                        <div className="empty-summary">
                            <Building2 size={42} />
                            <h3>No bank data yet</h3>
                            <p>Link a demo bank account to fetch the balance and show deposit or debit behavior.</p>
                        </div>
                    )}
                </section>
            </div>
        </div>
    );
};

export default BankConnectionDemo;
