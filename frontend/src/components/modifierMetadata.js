export const modifierMetadata = {
  "Mergers and Acquisitions": { scale: "0-10+ Points", logic: "Lower score = More favourable (less integration risk)" },
  "Amount of sensitive information": { scale: "Customer Type & E-com", logic: "B2C + Ecommerce increases data breach severity" },
  "Domain Encryption": { scale: "Encrypted Ratio", logic: "100% encrypted domains = Favourable" },
  "Geographic Spread": { scale: "Country Count", logic: "Wider spread increases regulatory complexity" },
  "Internet footprint": { scale: "Unique Domains × Customer Scale Multiplier", logic: "Unique web domains count × customer count multiplier (1.0 to 4.0)" },
  "Nature of services": { scale: "Sub-Industries × Appetite Multiplier", logic: "Unique sub-industries count × worst appetite (Prohibited x3, Restricted x2, Acceptable x1, Target x0.1)" },
  "Organizational Complexity": { scale: "Subsidiary Count", logic: "More subsidiaries = broader threat landscape" },
  "Privacy Regulation": { scale: "Compliance Mentions", logic: "Published policy + Compliance = Favourable" },
  "Seasonality of sales": { scale: "Coefficient of Variation", logic: "High variance means peak outages are devastating" },
  "Volatility/Recovery in Sales": { scale: "Adjusted Index Score (2-16)", logic: "D1+D2+D3 + Sales Overlay" },
  "Applicability of Privacy Regulation": { scale: "SIC Code Mapping", logic: "Strict industries (Health/Finance) increase liability" },
  "B2C End Products": { scale: "Business Model", logic: "Direct consumer interaction increases privacy risk" },
  "Years in business": { scale: "Age in Years", logic: "Older enterprise = more established and favourable" },
  "Cybersecurity Info": { scale: "Pillars Weighted Score", logic: "Certifications (40/50%) + Live Web Security (40/50%) + SEC CISO (20% Public)" },
  "Industry & Company Breach History": { scale: "Systemic + Idiosyncratic Risk Points", logic: "Industry DBIR Frequency (0-4 pts) + Company Incident Severity * Recency + Repeat Kicker (Private zero-breach floor: Average)" }
};
