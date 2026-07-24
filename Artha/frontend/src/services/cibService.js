import api from './api';

/**
 * Perform manual or on-demand CIB verification for a citizenship number
 * @param {string} citizenshipNumber 
 * @returns {Promise<Object>}
 */
export const verifyCibStatus = async (citizenshipNumber) => {
    const response = await api.post('/cib/verify', {
        citizenship_number: citizenshipNumber,
    });
    return response.data;
};
