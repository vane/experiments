# Test CRISPR logic for rs12913832 targeting using Bioconductor
source("utils.R")

# Sequence around rs12913832 (hg38 chr15:28,120,472)
# SNP is at index 52
target_sequence <- "TGTCTACCCTAAACATGTTCACAGGGTGAGCCACCTGGGCAGAATTAGAGAGTGACATCTTCCCTCAGCCCCAGTCTCTACTCCTACTTCCACCACTCCACCTTAATCTCTCA"
snp_pos <- 52 

cat("Testing CRISPR design logic using Biostrings...\n")

# Use the utility function
guides <- design_guides(target_sequence, guide_len = 20)

if (nrow(guides) > 0) {
  # Check which guides target the SNP
  guides$SNP_Targeted <- sapply(1:nrow(guides), function(i) {
    is_snp_targeted(guides$Start[i], guides$End[i], snp_pos)
  })
  
  cat("Found", nrow(guides), "potential guides.\n")
  targeted <- guides[guides$SNP_Targeted, ]
  
  if (nrow(targeted) > 0) {
    cat("\nSuccess: Found", nrow(targeted), "guides targeting the eye color SNP!\n")
    print(targeted)
  } else {
    cat("\nNo guides found that target the SNP directly.\n")
    print(guides)
  }
} else {
  cat("\nError: No guides found in the sequence.\n")
}
