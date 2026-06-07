// src/components/PricingPage.jsx
import React, { useState } from 'react';
import {
  Container,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Box,
  Switch,
  FormControlLabel,
  Chip,
  Divider,
} from '@mui/material';
import { CheckCircle, RadioButtonUnchecked } from '@mui/icons-material';
import { pricingData } from '../data/pricingData';

const PricingPage = () => {
  const [isAnnual, setIsAnnual] = useState(false);

  const handleToggle = () => setIsAnnual(!isAnnual);

  return (
    <Container maxWidth="lg" sx={{ py: 8 }}>
      {/* Header Section */}
      <Box sx={{ textAlign: 'center', mb: 6 }}>
        <Typography variant="h2" component="h2" gutterBottom fontWeight={600}>
          Simple, Transparent Pricing
        </Typography>
        <Typography variant="h6" color="text.secondary" sx={{ maxWidth: 600, mx: 'auto' }}>
          Choose the plan that's right for you. All plans include a 14-day free trial with no credit card required.
        </Typography>
      </Box>

      {/* Billing Toggle */}
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', mb: 6, gap: 2 }}>
        <FormControlLabel
          control={
            <Switch
              checked={isAnnual}
              onChange={handleToggle}
              color="primary"
            />
          }
          label={isAnnual ? "Billed Annually" : "Billed Monthly"}
        />
        {isAnnual && (
          <Chip
            label="Save 17%"
            color="success"
            size="small"
            sx={{ fontWeight: 500 }}
          />
        )}
      </Box>

      {/* Pricing Cards Grid */}
      <Grid container spacing={4} justifyContent="center">
        {pricingData.map((tier) => {
          const currentPrice = isAnnual ? tier.annualPrice : tier.monthlyPrice;
          const savings = Math.round((1 - (tier.annualPrice / (tier.monthlyPrice * 12))) * 100);

          return (
            <Grid item key={tier.id} xs={12} md={4}>
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
                {/* Popular Badge */}
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

                  {/* Price */}
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

                  {/* Description */}
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
            </Grid>
          );
        })}
      </Grid>

      {/* Footer Note */}
      <Box sx={{ textAlign: 'center', mt: 6 }}>
        <Typography variant="body2" color="text.secondary">
          All plans include 14-day free trial. No credit card required. Cancel anytime.
        </Typography>
      </Box>
    </Container>
  );
};

export default PricingPage;

