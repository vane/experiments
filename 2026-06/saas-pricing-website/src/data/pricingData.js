// src/data/pricingData.js
export const pricingData = [
  {
    id: 1,
    name: "Basic",
    monthlyPrice: 19,
    annualPrice: 190,
    description: "Perfect for individuals and small projects just getting started.",
    isPopular: false,
    ctaText: "Get Started",
    ctaLink: "#",
    features: [
      { text: "Up to 5 Projects", included: true },
      { text: "10GB Cloud Storage", included: true },
      { text: "Basic Analytics", included: true },
      { text: "Email Support", included: true },
      { text: "1 Team Member", included: true },
      { text: "Advanced Analytics", included: false },
      { text: "Custom Integrations", included: false },
      { text: "24/7 Priority Support", included: false },
    ]
  },
  {
    id: 2,
    name: "Pro",
    monthlyPrice: 49,
    annualPrice: 490,
    description: "For growing teams that need more power and flexibility.",
    isPopular: true,
    ctaText: "Start Free Trial",
    ctaLink: "#",
    features: [
      { text: "Unlimited Projects", included: true },
      { text: "100GB Cloud Storage", included: true },
      { text: "Advanced Analytics", included: true },
      { text: "Custom Integrations", included: true },
      { text: "24/7 Priority Support", included: true },
      { text: "Up to 10 Team Members", included: true },
      { text: "SSO Authentication", included: true },
    ]
  },
  {
    id: 3,
    name: "Enterprise",
    monthlyPrice: 99,
    annualPrice: 990,
    description: "For large organizations with custom needs and dedicated support.",
    isPopular: false,
    ctaText: "Contact Sales",
    ctaLink: "#",
    features: [
      { text: "Unlimited Cloud Storage", included: true },
      { text: "Unlimited Team Members", included: true },
      { text: "Dedicated Account Manager", included: true },
      { text: "Custom SLA", included: true },
      { text: "On-premise Deployment Option", included: true },
      { text: "Audit Logs", included: true },
      { text: "Custom Integrations", included: true },
    ]
  }
];

