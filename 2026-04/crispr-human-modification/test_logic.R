# Test CRISPR logic for multiple eye color targets using Bioconductor
source("utils.R")

# Target configurations
targets <- list(
  "Brown/Blue" = list(
    seq = "TGTCTACCCTAAACATGTTCACAGGGTGAGCCACCTGGGCAGAATTAGAGAGTGACATCTTCCCTCAGCCCCAGTCTCTACTCCTACTTCCACCACTCCACCTTAATCTCTCA",
    snp_pos = 52
  ),
  "Dark Brown" = list(
    seq = "CTGATGAGCCATCAAAAGAGGGACAGCCTGGGTCTGCTGCAGGGAGGCCCGGATGCTGATGGACACCGTCTCTCTGCAGAACGAAACAACGACCTTACTGT",
    snp_pos = 52
  ),
  "Green" = list(
    seq = "TGATGTGAATGACAGCTTTGTTTCATCCACTTTGGTGGGTAAAAGAAGGCAAATTCCCCTGTGGTACTTTTGGTGCCAGGTTTAGCCATATGACGAAGCT",
    snp_pos = 51
  ),
  "Hazel" = list(
    seq = "GGACGGCCGCGATGAGACAGAGCATGATGATCATGGCCCACACCCGTCCCCGGGAGAGCCGGTATGCCTGGCCACACACACACAGAGAGAGTACAAGCCAG",
    snp_pos = 52
  ),
  "Amber" = list(
    seq = "TGTAATCCCGGCACTTTGGGAGGCCGAGGTGGGCGGATCACGAGGTCAGGAGATCGAGACCATCTTGGCTAACATGGTGAAACCCCGTCTCTACTAAAAAT",
    snp_pos = 52
  ),
  "Grey" = list(
    seq = "CATGCACCACCATGCCTGGCTAATTTTTGTTCTTTAGTAGAGATGGGGTTTTACCATATTGGCAAGGCTGGTCTCAAACTCCTGACCTCAAACAATCCACC",
    snp_pos = 52
  ),
  "Light Blue" = list(
    seq = "TAGACCAGAAACTTTTAGAAGACATCCTTAGGAGAGAGAAAGACTTACAAGAATAAAGTGAGGAAAACACGGAGTTGATGCACAAGCCCCAACATCCAACC",
    snp_pos = 52
  ),
  "Blue/Green" = list(
    seq = "TCCTGATGGACTCTAGGTAACTTACTCCTTTGCTTTCCAAAAGAGTAATAAGAAAAGCTATATTTAATTTAATGTGGTTCCATTTGTAGAGAGAAATAATA",
    snp_pos = 52
  ),
  "Red" = list(
    seq = "AACAAACACAAAAATAGACAAATAGGATTACTTCAAACTAAAAATCTCCAAGCGACCAAGAAAACAATTAACATGATAGACAGACAACTTACACAATAGG",
    snp_pos = 51
  ),
  # Nose targets
  "Nose Wing Breadth" = list(
    seq = "ATCTCTTTATGGGTGCTCTTCAGGGGTATCTTTTCAGGGTTCTTGGTCAGCTGGTAAGTGTTACAATAATATCTCTTTTGAATATGTAACTATTATGCATT",
    snp_pos = 52
  ),
  "Nose Protrusion" = list(
    seq = "GCTTATCACCAACTTTATGAAACTTACTGACTCTAAGTAGAGAACGAGCCGGTCAGGTTTCAAGTTTTTCTTAAATGTCAATATTCTAAAAAAGAAAGCTG",
    snp_pos = 52
  ),
  "Columella Inclination" = list(
    seq = "TCAGCAATAAGTTCAGTATATGTCTATATACTTTGGGAAGTAGTTTTTGCATTGCTCAGCACCCTGTATTGCTCTGTTTCTACAGAGAACACTCTAAGAGA",
    snp_pos = 52
  ),
  "Nose Width" = list(
    seq = "TGCTACTCCTGATCTCTGCCTCCCAGCAGCTTCTGTCTAGCCTGCTGTCACCAGTCATGGGTTGGGATGGCCCTCTGTGTCTCAACGCAAAGGCCACACTT",
    snp_pos = 52
  ),
  "Nose Length" = list(
    seq = "CTCTGGCCTGCCTTGCAGCCTTCGTGTATGAGCCCCGGTCTCACCCCAGGGTGCACCGGGCGCTCCTGTCCACCCCACCCCCGCAGCCCACTGGGCCGGGT",
    snp_pos = 52
  ),
  # Ear targets
  "Ear Shape" = list(
    seq = "CATCCCTCTTCAGGCCGAAGCTCTCGGCGAGGTGGCGCCACGTTTTCACAACAGCCTTCTCAGAGTTGTACGTGGAGCTGAGCATTCGGCTAGTCTTCTCG",
    snp_pos = 52
  ),
  "Lobe Attachment" = list(
    seq = "aattaggatttgaacccgagcagcctggtcccagagcccatgtgctGGAGCTACAATACCGATCCCTCTGGACAGACAGGTAAACGATGGTTGACCATGGG",
    snp_pos = 52
  ),
  "Vertical Ear Length" = list(
    seq = "ttggttAAgaatgaaataaatctgtgttctaatctcatatacgttattaactagacacaaagaccttgagaaagtcattagcccttccagacagtattatt",
    snp_pos = 52
  ),
  "Darwin's Tubercle" = list(
    seq = "ATGCGTCTCACCCCCAACTTTACAGGTAGGGAGGCTGAGTGGGGACAGAGTATAGTTTCTGCCTCTCTGGCCTGACGCTCTACACTGTCCCACTTTTCTGA",
    snp_pos = 52
  ),
  "Lobe Size" = list(
    seq = "aaggagttcatgtagtgatgcccaagcactaagttgtgcagctcaaatagtggtggaatgatagggtagatgagcaagaatctgcccaggcagcagcccta",
    snp_pos = 52
  )
)

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
