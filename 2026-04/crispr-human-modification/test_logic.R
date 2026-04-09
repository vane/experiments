library(testthat)
source("utils.R")

# Load target configurations
source("targets/eyes.R")
source("targets/nose.R")
source("targets/ears.R")

targets <- c(targets_eyes, targets_nose, targets_ears)

context("CRISPR Design Logic")

for (name in names(targets)) {
  test_that(paste("Target identification and SNP hit for:", name), {
    target <- targets[[name]]
    
    # We expect design_guides to run without error and find potential guides
    expect_error(guides <- design_guides(target$seq, guide_len = 20), NA)
    expect_gt(nrow(guides), 0)
    
    # Check SNP targeting
    guides$SNP_Targeted <- sapply(seq_len(nrow(guides)), function(i) {
      is_snp_targeted(guides$Start[i], guides$End[i], target$snp_pos)
    })
    
    targeted <- guides[guides$SNP_Targeted, ]
    
    # Known targets that do NOT have a guide hitting the SNP in the 101bp context
    # based on previous analysis. We expect them to have 0 hits but still pass the test.
    no_hit_expected <- c("Columella Inclination", "Vertical Ear Length")
    
    if (name %in% no_hit_expected) {
      expect_equal(nrow(targeted), 0, label = paste("Expected 0 hits for", name))
    } else {
      expect_gt(nrow(targeted), 0, label = paste("Expected hits for", name))
    }
  })
}
