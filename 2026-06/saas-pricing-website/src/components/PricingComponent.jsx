// src/components/PricingComponent.jsx
import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Button,
  Box,
  Chip,
  Divider,
} from '@mui/material';
import { CheckCircle, RadioButtonUnchecked } from '@mui/icons-material';
import PropTypes from 'prop-types';

const PricingComponent = ({ tier, isAnnual }) => {
  // Calculate price and savings from the full tier data object
  const currentPrice = isAnnual ? tier.annualPrice : tier.monthlyPrice;
  const savings = Math.round(
    (1 - (tier.annualPrice / (tier.monthlyPrice * 12))) * 100
  );

  return (
    <Card
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        border: tier.isPopular ? '2px solid' : '1px solid',
        borderColor: tier.isPopular ? 'primary.main' : 'divider',
        boxShadow: tier.isPopular ? 6 : 1,
        transition: 'box-shadow 0.3s ease',
        '&:hover': {
          boxShadow: tier.isPopular ? 10 : 3,
        },
      }}
    >
      {/* Popular Badge (only renders if tier.isPopular is true) */}
      {tier.isPopular && (
        <Chip
          label="Most Popular"
          color="primary"
          size="small"
          sx={{
            position: 'absolute',
            top: 16,
            right: 16,
            zIndex: 1,
            fontWeight: 500,
          }}
        />
      )}

      <CardContent sx={{ flexGrow: 1, p: 4 }}>
        {/* Tier Name */}
        <Typography
          variant="h5"
          component="h3"
          gutterBottom
          sx={{ textAlign: 'center', fontWeight: 600 }}
        >
          {tier.name}
        </Typography>

        {/* Price Section */}
        <Box sx={{ textAlign: 'center', mb: 2 }}>
          <Typography variant="h3" component="div" color="text.primary" fontWeight={700}>
            ${currentPrice}
          </Typography>
          <Typography variant="body1" color="text.secondary">
            {isAnnual ? '/year, billed annually' : '/month'}
          </Typography>
          {isAnnual && (
            <Typography variant="body2" color="success.main" sx={{ mt: 0.5 }}>
              Save {savings}% with annual billing
            </Typography>
          )}
        </Box>

        {/* Tier Description */}
        <Typography
          variant="body1"
          color="text.secondary"
          sx={{ mb: 3, textAlign: 'center' }}
        >
          {tier.description}
        </Typography>

        <Divider sx={{ mb: 3 }} />

        {/* Features List */}
        <Box component="ul" sx={{ listStyle: 'none', p: 0, m: 0, mb: 4 }}>
          {tier.features.map((feature, idx) => (
            <Box
              component="li"
              key={idx}
              sx={{
                display: 'flex',
                alignItems: 'center',
                mb: 1.5,
                color: feature.included ? 'text.primary' : 'text.disabled',
              }}
            >
              {feature.included ? (
                <CheckCircle sx={{ mr: 1.5, fontSize: 20, color: 'primary.main' }} />
              ) : (
                <RadioButtonUnchecked sx={{ mr: 1.5, fontSize: 20 }} />
              )}
              <Typography variant="body2">{feature.text}</Typography>
            </Box>
          ))}
        </Box>

        {/* CTA Button */}
        <Button
          variant={tier.isPopular ? 'contained' : 'outlined'}
          fullWidth
          size="large"
          href={tier.ctaLink}
          sx={{ py: 1.5, textTransform: 'none', fontWeight: 600 }}
        >
          {tier.ctaText}
        </Button>
      </CardContent>
    </Card>
  );
};

// Prop types for clarity (optional but recommended)
PricingComponent.propTypes = {
  /** Full pricing tier data object from pricingData.js */
  tier: PropTypes.shape({
    id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired,
    monthlyPrice: PropTypes.number.isRequired,
    annualPrice: PropTypes.number.isRequired,
    description: PropTypes.string.isRequired,
    isPopular: PropTypes.bool.isRequired,
    ctaText: PropTypes.string.isRequired,
    ctaLink: PropTypes.string.isRequired,
    features: PropTypes.arrayOf(
      PropTypes.shape({
        text: PropTypes.string.isRequired,
        included: PropTypes.bool.isRequired,
      })
    ).isRequired,
  }).isRequired,
  /** Billing toggle state from parent */
  isAnnual: PropTypes.bool.isRequired,
};

export default PricingComponent;

