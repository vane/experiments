# Test CRISPR logic for multiple eye color targets using Bioconductor
source("utils.R")

# Load target configurations
source("targets/eyes.R")
source("targets/nose.R")
source("targets/ears.R")

targets <- c(targets_eyes, targets_nose, targets_ears)

cat("Testing CRISPR design logic for multiple phenotypic targets...\n\n")

for (name in names(targets)) {
  target <- targets[[name]]
  cat("--- Testing Target:", name, "---\n")
  
  guides <- design_guides(target$seq, guide_len = 20)
  
  if (nrow(guides) > 0) {
    guides$SNP_Targeted <- sapply(1:nrow(guides), function(i) {
      is_snp_targeted(guides$Start[i], guides$End[i], target$snp_pos)
    })
    
    cat("Found", nrow(guides), "potential guides.\n")
    targeted <- guides[guides$SNP_Targeted, ]
    
    if (nrow(targeted) > 0) {
      cat("Success: Found", nrow(targeted), "guides targeting the SNP!\n")
      print(targeted)
    } else {
      cat("Notice: No guides found that target the SNP directly in this snippet.\n")
    }
  } else {
    cat("Error: No guides found in the sequence.\n")
  }
  cat("\n")
}
