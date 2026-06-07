// src/PricingSection.jsx
import React from 'react';
import {
    Box,
    Container,
    Grid,
    Typography,
} from '@mui/material';
import { pricingData } from './pricingData';
import PricingCard from './PricingCard';

const PricingSection = () => {
    return (
        <Box sx={{ py: 8, bgcolor: '#f9f9f9', minHeight: '100vh' }}>
            <Container maxWidth="lg">
                {/* Header Section */}
                <Box sx={{ textAlign: 'center', mb: 6 }}>
                    <Typography variant="h4" component="h1" fontWeight="bold" gutterBottom>
                        Simple, Transparent Pricing
                    </Typography>
                    <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 600, mx: 'auto' }}>
                        Choose the plan that best fits your needs. No hidden fees, cancel anytime.
                    </Typography>
                </Box>

                {/* Pricing Grid */}
                <Grid sx={{alignContent: 'center', justifyContent: 'space-evenly'}} container spacing={1}>
                    {pricingData.map((plan) => (
                        <Grid item xs={12} md={6} lg={4} key={plan.id}>
                            <PricingCard plan={plan} />
                        </Grid>
                    ))}
                </Grid>
            </Container>
        </Box>
    );
};

export default PricingSection;
