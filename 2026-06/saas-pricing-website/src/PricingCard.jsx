// src/PricingCard.jsx
import React from 'react';
import {
    Box,
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

const PricingCard = ({ plan }) => {
    const theme = useTheme();
    const { title, description, price, buttonText, features, highlight } = plan;

    // Styles for the pricing card
    const cardStyles = {
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        borderRadius: 2,
        transition: 'transform 0.3s ease, box-shadow 0.3s ease',
        border: highlight ? `2px solid ${theme.palette.primary.main}` : '1px solid #e0e0e0',
        position: 'relative',
        backgroundColor: highlight ? '#fafafa' : '#fff',
        '&:hover': {
            transform: 'translateY(-5px)',
            boxShadow: theme.shadows[8],
        },
    };

    return (
        <Card sx={cardStyles}>
            {highlight && (
                <Box
                    sx={{
                        position: 'absolute',
                        top: 16,
                        left: '50%',
                        transform: 'translateX(-50%)',
                        zIndex: 1,
                    }}
                >
                    <Chip
                        label="Most Popular"
                        size="small"
                        color="primary"
                        sx={{
                            boxShadow: 2,
                            height: 32,
                            lineHeight: '32px',
                        }}
                    />
                </Box>
            )}

            <CardContent
                sx={{
                    flexGrow: 1,
                    textAlign: 'center',
                    pt: highlight ? 8 : 3,
                    pb: 4,
                }}
            >
                <Typography variant="h6" fontWeight="600" gutterBottom>
                    {title}
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                    {description}
                </Typography>

                <Box sx={{ my: 3 }}>
                    <Typography variant="h3" fontWeight="bold" component="div">
                        {price.currency}
                        <span>{price.amount}</span>
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        {price.period}
                    </Typography>
                </Box>

                <Button
                    fullWidth
                    variant={plan.variant}
                    size="large"
                    sx={{ mb: 4, fontWeight: 'bold' }}
                >
                    {buttonText}
                </Button>

                <List disablePadding>
                    {features.map((feature) => (
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
    );
};

export default PricingCard;
