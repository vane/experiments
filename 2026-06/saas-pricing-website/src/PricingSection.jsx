// src/PricingSection.jsx
import React from 'react';
import {
    Box,
    Container,
    Grid,
    Card,
    CardContent,
    Typography,
    Button,
    Chip,
    List,
    ListItem,
    ListItemIcon,
    ListItemText,
    useTheme,
} from '@mui/material';
import { Check } from '@mui/icons-material';
import { pricingData } from './pricingData';

const PricingSection = () => {
    const theme = useTheme();

    // Styles for the pricing card
    const cardStyles = (isPopular) => ({
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        borderRadius: 1,
        transition: 'transform 0.3s ease, box-shadow 0.3s ease',
        border: isPopular ? `2px solid ${theme.palette.primary.main}` : '1px solid #e0e0e0',
        position: 'relative',
        backgroundColor: isPopular ? '#fafafa' : '#fff',
        padding: 2,
        // 1. Add top margin to create space for the chip
        '&:hover': {
            transform: 'translateY(-5px)',
            boxShadow: theme.shadows[8],
        },
    });

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
                <Grid container spacing={4} justifyContent="center">
                    {pricingData.map((plan) => (
                        <Grid item xs={12} md={6} lg={4} key={plan.id}>
                            <Card sx={cardStyles(plan.highlight)}>
                                {plan.highlight && (
                                    <Box
                                        sx={{
                                            position: 'absolute',
                                            top: 16, // 2. Move it further up to ensure it clears the border
                                            left: '50%',
                                            transform: 'translateX(-50%)',
                                            zIndex: 1,
                                        }}
                                    >
                                        <Chip
                                            label="Most Popular"
                                            size="small"
                                            color="primary"
                                            // Optional: Add a small shadow to the chip itself for better visibility
                                            sx={{ boxShadow: 2 }}
                                        />
                                    </Box>
                                )}

                                {/* 3. Add paddingTop to content so text doesn't overlap the chip area */}
                                <CardContent sx={{
                                    flexGrow: 1,
                                    textAlign: 'center',
                                    pt: plan.highlight ? 6 : 3,
                                    pb: 4
                                }}>
                                    <Typography variant="h6" fontWeight="600" gutterBottom>
                                        {plan.title}
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary" paragraph>
                                        {plan.description}
                                    </Typography>

                                    <Box sx={{ my: 3 }}>
                                        <Typography variant="h3" fontWeight="bold" component="div">
                                            {plan.price.currency}
                                            <span>{plan.price.amount}</span>
                                        </Typography>
                                        <Typography variant="body2" color="text.secondary">
                                            {plan.price.period}
                                        </Typography>
                                    </Box>

                                    <Button
                                        fullWidth
                                        variant={plan.variant}
                                        size="large"
                                        sx={{ mb: 4, fontWeight: 'bold' }}
                                    >
                                        {plan.buttonText}
                                    </Button>

                                    <List disablePadding>
                                        {plan.features.map((feature) => (
                                            <ListItem key={feature} disablePadding sx={{ py: 0.5 }}>
                                                <ListItemIcon sx={{ minWidth: 36, color: 'success.main' }}>
                                                    <Check fontSize="small" />
                                                </ListItemIcon>
                                                <ListItemText
                                                    primary={feature}
                                                    primaryTypographyProps={{ variant: 'body2', color: 'text.secondary' }}
                                                />
                                            </ListItem>
                                        ))}
                                    </List>
                                </CardContent>
                            </Card>
                        </Grid>
                    ))}
                </Grid>
            </Container>
        </Box>
    );
};

export default PricingSection;
