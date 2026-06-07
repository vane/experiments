// src/components/PricingPage.jsx
import React, { useState } from 'react';
import {
  Container,
  Grid,
  Box,
  Typography,
  Switch,
  FormControlLabel,
  Chip,
} from '@mui/material';
import { pricingData } from '../data/pricingData';
import PricingComponent from './PricingComponent';

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

      {/* Pricing Cards Grid - Pass full tier object to each component */}
      <Grid container spacing={4} justifyContent="center">
        {pricingData.map((tier) => (
          <Grid item key={tier.id} xs={12} md={4}>
            <PricingComponent tier={tier} isAnnual={isAnnual} />
          </Grid>
        ))}
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

