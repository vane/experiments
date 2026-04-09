# CRISPR Eye Color Modification Template

This project provides a template R/Shiny application for designing CRISPR/Cas9 guide RNAs (gRNAs) to modify human eye color at the genetic level.

## Biological Context

Eye color is primarily determined by the expression levels of the `OCA2` gene. A critical regulatory element for `OCA2` is located in an intron of the neighboring `HERC2` gene. Specifically, the Single Nucleotide Polymorphism (SNP) **rs12913832** (chr15:28,120,472 in hg38) acts as an enhancer:
- **Allele A (or T):** Associated with brown eyes (higher `OCA2` expression).
- **Allele G (or C):** Associated with blue eyes (lower `OCA2` expression).

By using CRISPR/Cas9 (or more advanced tools like Base Editors), one can theoretically target this site to modulate `OCA2` expression and thus influence the phenotype.

## Application Features

- **Multi-Target Support:** Supports designing guides for Brown/Blue (HERC2/OCA2), Green (IRF4), and Red (TYR) eye color phenotypes.
- **Sequence Visualization:** Displays the genomic context and highlights the target SNP for each locus.
- **gRNA Design:** Uses the Bioconductor `Biostrings` library to search for "NGG" PAM sites and design custom length guides.
- **Target Analysis:** Identifies whether the SNP is located within the guide sequence or the PAM.

## Prerequisites

To run this application, you need R installed with the following libraries:

### CRAN Libraries
```R
install.packages("shiny")
```

### Bioconductor Libraries
```R
if (!require("BiocManager", quietly = TRUE))
    install.packages("BiocManager")

BiocManager::install(c("Biostrings", "GenomicRanges"))
```

### Verification Script

A verification script `test_logic.R` is included to test the CRISPR design logic outside the Shiny app:
```bash
Rscript test_logic.R
```

## How to Run

1. Open R or RStudio.
2. Set your working directory to this project folder.
3. Run the following command:
   ```R
   shiny::runApp()
   ```

## Disclaimer

This application is for educational and computational template purposes only. Genomic modification in humans is subject to strict ethical and legal regulations.
