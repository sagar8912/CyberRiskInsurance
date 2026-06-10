export const targetCompany = {
  name: "Liberty Mutual Insurance",
  domain: "libertymutual.com",
};

export const reconciledProfile = {
  revenue: "Not Available",
  subsidiariesCount: 1,
  acquisitionsCount: 0,
  customerType: "B2C",
  ecommercePlatform: true,
  countriesOfOps: "US",
  privacyPolicy: true,
};

export const factCheckerClaims = [
  { claim: "revenue", status: "Unsupported", sourceCount: 1 },
  { claim: "subsidiaries_count", status: "Partially Verified", sourceCount: 2 },
  { claim: "acquisitions_count", status: "Unsupported", sourceCount: 0 },
  { claim: "customer_type", status: "Unsupported", sourceCount: 0 },
  { claim: "has_ecommerce", status: "Partially Verified", sourceCount: 1 },
  { claim: "privacy_policy_published", status: "Verified", sourceCount: 2 },
];

export const modifiers = [
  { id: 1, name: "Mergers and Acquisitions", rating: "VERY FAVOURABLE", score: "0.0", rationale: "No recent acquisitions, favourable." },
  { id: 2, name: "Amount of sensitive information", rating: "PARTIALLY UNFAVOURABLE", score: "0.0", rationale: "B2C customer type and ecommerce presence increase risk." },
  { id: 3, name: "Domain Encryption", rating: "FAVOURABLE", score: "1/1", rationale: "Only one domain is https encrypted, partially favourable." },
  { id: 4, name: "Geographic Spread", rating: "FAVOURABLE", score: "1.0", rationale: "USA presence and limited continent spread, partially favourable." },
  { id: 5, name: "Internet footprint", rating: "FAVOURABLE", score: "3.0", rationale: "Enterprise scale with one domain, partially favourable." },
  { id: 6, name: "Nature of services", rating: "AVERAGE", score: "medium_risk", rationale: "Medium risk services appetite, neutral." },
  { id: 7, name: "Organizational Complexity", rating: "VERY FAVOURABLE", score: "1.0", rationale: "Single subsidiary, relatively simple organizational structure, favourable." },
  { id: 8, name: "Privacy Regulation", rating: "FAVOURABLE", score: "2.0", rationale: "Published policy and compliance with GDPR and CCPA, favourable." },
  { id: 9, name: "Seasonality of sales", rating: "AVERAGE", score: "0.0", rationale: "Insufficient quarterly revenue data, unable to assess." },
  { id: 10, name: "Volatility/Recovery in Sales", rating: "PARTIALLY UNFAVOURABLE", score: "3.67", rationale: "Moderate digital exposure, disruption speed, and recovery complexity, partially unfavourable." },
  { id: 11, name: "Applicability of Privacy Regulation", rating: "AVERAGE", score: "0.0", rationale: "Operates in strict regions and has ecommerce, partially unfavourable." },
  { id: 12, name: "B2C End Products", rating: "FAVOURABLE", score: "0.0", rationale: "B2C customer type, average risk." },
  { id: 13, name: "Years in business", rating: "VERY FAVOURABLE", score: "114", rationale: "Long-standing company, favourable." }
];

export const finalVerdict = {
  riskCategory: "FAVOURABLE",
  underwritingScore: "33.3%",
  confidenceBand: "Low",
  humanEscalation: true,
};
