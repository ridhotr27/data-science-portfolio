import React from 'react';
import { Card } from '../ui/Card';

const shared = [
  'CSV or XLSX, up to 5 MB',
  'Maximum 10,000 data rows and 50 columns',
  'The first row must contain clear column names',
  'Do not upload confidential, personal, or sensitive data',
];

const content = {
  eda: {
    description: 'Use a general tabular dataset where each row represents one observation. Numeric, categorical, and date columns are supported; a target column is optional.',
    items: ['EDA describes structure, quality, distributions, and relationships. It does not train a prediction model.'],
    example: 'customer_id, age, city, signup_date, total_spend, optional_target',
  },
  customer360: {
    description: 'Each row should represent a transaction or transaction line item. Customer ID is required; transaction ID, transaction date, and revenue are recommended.',
    items: [
      'Revenue may instead be calculated from quantity × unit price.',
      'Product, category, channel, store, and demographics are optional; missing fields disable related analytics.',
      'Historical CLV is descriptive. Annual CLV is an extrapolation, not a predictive ML model.',
    ],
    example: 'customer_id, transaction_id, transaction_date, revenue, product, category, channel',
  },
};

export function DataRequirements({ type }) {
  const details = content[type];
  return <Card title="Data Requirements" eyebrow="Before you upload" className="data-requirements">
    <p>{details.description}</p>
    <ul>{[...shared, ...details.items].map((item) => <li key={item}>{item}</li>)}</ul>
    <p className="muted"><strong>Example columns:</strong> <code>{details.example}</code></p>
  </Card>;
}
