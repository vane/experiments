# CRISPR Eye Color Modification Template

This project provides a template R/Shiny application for designing CRISPR/Cas9 guide RNAs (gRNAs) to modify human physical traits (eye color, nose morphology, and ear morphology) at the genetic level.

## Biological Context

### Eye Color
Eye color is primarily determined by the expression levels of the `OCA2` gene. A critical regulatory element for `OCA2` is located in an intron of the neighboring `HERC2` gene. Specifically, the Single Nucleotide Polymorphism (SNP) **rs12913832** acts as an enhancer.

### Nose Morphology
Facial morphology, including nose size and shape, is a complex polygenic trait. Several genes have been identified as key regulators:
- **PAX1**: Associated with nose wing breadth.
- **DCHS2**: Influences nose protrusion and columella inclination.
- **DHX35**: Associated with nose width.
- **IGSF3**: Associated with nose length.

### Ear Morphology
Ear shape and size are also heritable traits with several identified genetic drivers:
- **EDAR**: Influences ear protrusion and shape (prominent antihelix superior crus).
- **TBX15/WARS2**: Locus associated with lobe attachment and size.
- **8q24.13**: Region associated with vertical ear length.

### Teeth Morphology
Dental development is regulated by a complex network of signaling pathways (Wnt, BMP, FGF, Shh):
- **PAX9/MSX1**: Critical transcription factors for early odontogenesis; variations are linked to non-syndromic tooth agenesis.
- **WNT10A**: Key regulator of tooth number, shape, and size.
- **PITX2**: Determines tooth size and the patterning of the dental lamina.
- **EDAR**: Influences incisor shoveling and overall tooth crown dimensions.

## Application Features

- **Multi-Trait Support:** 
  - **Eye Color:** Brown/Blue, Dark Brown, Green, Hazel, Amber, Grey, Light Blue, Blue/Green, Red/Albinism, and Sectoral Heterochromia.
  - **Nose Morphology:** Wing Breadth, Protrusion, Columella Inclination, Width, and Length.
  - **Ear Morphology:** Shape, Lobe Attachment, Vertical Length, Darwin's Tubercle, and Lobe Size.
  - **Teeth Morphology:** Tooth Agenesis (PAX9/MSX1), Shape/Size (WNT10A/PITX2), and Incisor Shoveling.
- **Data Persistence:** Genomic sequences are stored as JSON artifacts in the `data/` directory.
- **Sequence Visualization:** Displays the genomic context and highlights the target SNP for each locus.
- **gRNA Design:** Uses the Bioconductor `Biostrings` library to search for "NGG" PAM sites and design custom length guides.
- **Target Analysis:** Identifies whether the SNP is located within the guide sequence or the PAM.

## Prerequisites

To run this application, you need R installed with the following libraries:

### CRAN Libraries
```R
install.packages(c("shiny", "bslib"))
```

### Bioconductor Libraries
```R
if (!require("BiocManager", quietly = TRUE))
    install.packages("BiocManager")

BiocManager::install(c("Biostrings", "IRanges"))
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

## Genomic Data History

The following genomic sequences were fetched from the UCSC Genome Browser (hg38) and are stored in the `data/` directory. Detailed `curl` commands used for fetching are available in [CURL.md](CURL.md).

### Eye Color Targets

| Phenotype | SNP ID | Chromosome | Position (hg38) | Artifact File |
|-----------|--------|------------|-----------------|---------------|
| Brown/Blue| rs12913832 | chr15 | 28,120,472 | `data/rs12913832.json` |
| Dark Brown| rs1800401 | chr15 | 28,014,907 | `data/rs1800401.json` |
| Green | rs12203592 | chr6 | 396,321 | `data/rs12203592.json` |
| Hazel | rs1800407 | chr15 | 27,985,172 | `data/rs1800407.json` |
| Amber | rs1540771 | chr20 | 34,138,092 | `data/rs1540771.json` |
| Grey | rs12896399 | chr14 | 92,113,279 | `data/rs12896399.json` |
| Light Blue| rs16891982 | chr5 | 33,951,556 | `data/rs16891982.json` |
| Blue/Green| rs1393350 | chr11 | 89,010,977 | `data/rs1393350.json` |
| Red | rs1042602 | chr11 | 89,230,557 | `data/rs1042602.json` |
| Sectoral Het.| rs121434257 | chr2 | 222,216,634 | `data/rs121434257.json` |

### Nose Morphology Targets

| Trait | SNP ID | Chromosome | Position (hg38) | Artifact File |
|-------|--------|------------|-----------------|---------------|
| Wing Breadth | rs927833 | chr20 | 22,060,939 | `data/rs927833.json` |
| Protrusion | rs2045323 | chr4 | 153,910,747 | `data/rs2045323.json` |
| Columella Incl. | rs12644248 | chr4 | 154,314,240 | `data/rs12644248.json` |
| Nose Width | rs2206437 | chr20 | 4,863,948 | `data/rs2206437.json` |
| Nose Length | rs647711 | chr1 | 116,167,664 | `data/rs647711.json` |

### Ear Morphology Targets

| Trait | SNP ID | Chromosome | Position (hg38) | Artifact File |
|-------|--------|------------|-----------------|---------------|
| Ear Shape | rs3827760 | chr2 | 108,897,145 | `data/rs3827760.json` |
| Lobe Attachment | rs6802174 | chr3 | 139,287,822 | `data/rs6802174.json` |
| Vertical Length | rs7812632 | chr8 | 121,878,655 | `data/rs7812632.json` |
| Darwin's Tubercle | rs1948400 | chr3 | 139,265,404 | `data/rs1948400.json` |
| Lobe Size | rs263156 | chr6 | 142,586,378 | `data/rs263156.json` |

### Teeth Morphology Targets

| Trait | SNP ID | Chromosome | Position (hg38) | Artifact File |
|-------|--------|------------|-----------------|---------------|
| Tooth Agenesis (PAX9) | rs4904210 | chr14 | 36,666,548 | `data/rs4904210.json` |
| Tooth Agenesis (MSX1) | rs8670 | chr4 | 4,863,149 | `data/rs8670.json` |
| Tooth Shape/Size | rs10168648 | chr2 | 35,202,027 | `data/rs10168648.json` |
| Tooth Size | rs3866831 | chr4 | 110,810,958 | `data/rs3866831.json` |
| Incisor Shoveling | rs3827760 | chr2 | 108,897,145 | `data/rs3827760.json` |

## Disclaimer

This application is for educational and computational template purposes only. Genomic modification in humans is subject to strict ethical and legal regulations.
