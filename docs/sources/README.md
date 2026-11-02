# Source notes

The two saved HTML documents are public U.S. Customs and Border Protection
(CBP) pages. They were fetched successfully during this prototype's source
check and are retained in this directory for reproducibility.

| Local file | Source | Intended use |
|---|---|---|
| `cbp_basic_importing_exporting.html` | https://www.cbp.gov/trade/basic-import-export | General importing/exporting background |
| `cbp_importer_exporter_tips.html` | https://www.cbp.gov/trade/basic-import-export/importer-exporter-tips | General importer guidance |

These pages are **not evidence about the fictional company's inventory,
shipment status, delay cause, or customer orders**. Those facts come only from
the synthetic CSV files in `data/`. The synthetic BrightHome playbook is
separately stored here and is clearly labeled; it is demo policy, not external
research or a real company's procedure.

## Source-selection checks

- The UNCTAD maritime report was accessible in an earlier check but returned
  HTTP 403 on a later re-fetch. It is not included as a dependable source.
- A NIST supplier-risk PDF was fetchable, but its cybersecurity supplier-risk
  focus does not directly support this shipment-delay workflow, so it was not
  added just to inflate the corpus.
- A relevant GAO supply-chain report URL was identified, but fetching failed
  during a later test because DNS resolution was unavailable. It was not saved
  or used.

This corpus is intentionally modest. Re-test URLs and relevance before adding
sources; accessibility alone does not make a document useful evidence.
