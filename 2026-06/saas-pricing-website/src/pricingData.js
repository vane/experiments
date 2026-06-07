// src/pricingData.js

export const pricingData = [
    {
        id: 'starter',
        title: 'Starter',
        description: 'Perfect for individuals and hobbyists.',
        price: { amount: '0', currency: '$', period: '/mo' },
        features: [
            '1 User Account',
            '5 Projects',
            'Community Support',
            'Basic Analytics',
        ],
        buttonText: 'Start for Free',
        isPopular: false,
        variant: 'outlined',
    },
    {
        id: 'pro',
        title: 'Professional',
        description: 'For growing teams and businesses.',
        price: { amount: '29', currency: '$', period: '/mo' },
        features: [
            '5 User Accounts',
            'Unlimited Projects',
            'Priority Email Support',
            'Advanced Analytics',
            'Custom Integrations',
        ],
        buttonText: 'Get Started',
        isPopular: true,
        variant: 'contained',
        highlight: true,
    },
    {
        id: 'enterprise',
        title: 'Enterprise',
        description: 'Scale your business with advanced tools.',
        price: { amount: '99', currency: '$', period: '/mo' },
        features: [
            'Unlimited Users',
            'Unlimited Projects',
            '24/7 Phone Support',
            'Dedicated Account Manager',
            'SSO & Security',
            'SLA Guarantee',
        ],
        buttonText: 'Contact Sales',
        isPopular: false,
        variant: 'outlined',
    },
];
