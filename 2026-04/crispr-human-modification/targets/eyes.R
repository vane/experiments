# Eye Color Targets
targets_eyes <- list(
  "Brown/Blue" = list(
    seq = "GCTCTCTGTGTCTGATCCAAGAGGCGAGGCCAGTTTCATTTGAGCATTAAATGTCAAGTTCTGCACGCTATCATCATCAGGGGCCGAGGCTTCTCTTTGTT",
    snp_pos = 52,
    locus = "chr15:28,120,472 (hg38)",
    snp_id = "rs12913832 (HERC2/OCA2)",
    phenotype = "Major determinant of eye color (Brown/Blue).",
    color = "brown"
  ),
  "Dark Brown" = list(
    # rs1800401 (OCA2)
    seq = "CTGATGAGCCATCAAAAGAGGGACAGCCTGGGTCTGCTGCAGGGAGGCCCGGATGCTGATGGACACCGTCTCTCTGCAGAACGAAACAACGACCTTACTGT",
    snp_pos = 52,
    locus = "chr15:28,014,907 (hg38)",
    snp_id = "rs1800401 (OCA2)",
    phenotype = "Associated with deep brown pigmentation.",
    color = "#5C4033"
  ),
  "Green" = list(
    # rs12203592 (IRF4)
    seq = "TGATGTGAATGACAGCTTTGTTTCATCCACTTTGGTGGGTAAAAGAAGGCAAATTCCCCTGTGGTACTTTTGGTGCCAGGTTTAGCCATATGACGAAGCT",
    snp_pos = 51,
    locus = "chr6:396,321 (hg38)",
    snp_id = "rs12203592 (IRF4)",
    phenotype = "Associated with intermediate (Green/Hazel) eye color.",
    color = "green"
  ),
  "Hazel" = list(
    # rs1800407 (OCA2)
    seq = "GGACGGCCGCGATGAGACAGAGCATGATGATCATGGCCCACACCCGTCCCCGGGAGAGCCGGTATGCCTGGCCACACACACACAGAGAGAGTACAAGCCAG",
    snp_pos = 52,
    locus = "chr15:27,985,172 (hg38)",
    snp_id = "rs1800407 (OCA2)",
    phenotype = "Associated with green/hazel eye color variations.",
    color = "#8E7618"
  ),
  "Amber" = list(
    # rs1540771 (ASIP)
    seq = "TGTAATCCCGGCACTTTGGGAGGCCGAGGTGGGCGGATCACGAGGTCAGGAGATCGAGACCATCTTGGCTAACATGGTGAAACCCCGTCTCTACTAAAAAT",
    snp_pos = 52,
    locus = "chr20:34,138,092 (hg38)",
    snp_id = "rs1540771 (ASIP)",
    phenotype = "Associated with golden/amber eye color.",
    color = "#FFBF00"
  ),
  "Grey" = list(
    # rs12896399 (SLC24A4)
    seq = "CATGCACCACCATGCCTGGCTAATTTTTGTTCTTTAGTAGAGATGGGGTTTTACCATATTGGCAAGGCTGGTCTCAAACTCCTGACCTCAAACAATCCACC",
    snp_pos = 52,
    locus = "chr14:92,113,279 (hg38)",
    snp_id = "rs12896399 (SLC24A4)",
    phenotype = "Associated with blue/grey eye color and blonde hair.",
    color = "grey"
  ),
  "Light Blue" = list(
    # rs16891982 (SLC45A2)
    seq = "TAGACCAGAAACTTTTAGAAGACATCCTTAGGAGAGAGAAAGACTTACAAGAATAAAGTGAGGAAAACACGGAGTTGATGCACAAGCCCCAACATCCAACC",
    snp_pos = 52,
    locus = "chr5:33,951,556 (hg38)",
    snp_id = "rs16891982 (SLC45A2)",
    phenotype = "Common variant predicting light iris color.",
    color = "lightblue"
  ),
  "Blue/Green" = list(
    # rs1393350 (TYRP1 locus area)
    seq = "TCCTGATGGACTCTAGGTAACTTACTCCTTTGCTTTCCAAAAGAGTAATAAGAAAAGCTATATTTAATTTAATGTGGTTCCATTTGTAGAGAGAAATAATA",
    snp_pos = 52,
    locus = "chr11:89,010,977 (hg38)",
    snp_id = "rs1393350 (near TYRP1)",
    phenotype = "Associated with blue/green eye color variations.",
    color = "cyan"
  ),
  "Red" = list(
    # rs1042602 (TYR)
    seq = "AACAAACACAAAAATAGACAAATAGGATTACTTCAAACTAAAAATCTCCAAGCGACCAAGAAAACAATTAACATGATAGACAGACAACTTACACAATAGG",
    snp_pos = 51,
    locus = "chr11:89,230,557 (hg38)",
    snp_id = "rs1042602 (TYR)",
    phenotype = "Associated with oculocutaneous albinism (Reddish/Pink eyes).",
    color = "red"
  ),
  "Sectoral Heterochromia" = list(
    # rs121434257 (PAX3)
    seq = "AAAGGACTGAGGGCATCTATGATGCGCCATTTGGCAAATGGCTGTAATTCCCAGCCTTTGCTCAAGGGAAAAGATACATTAGAGACACAAAACAAAAACCA",
    snp_pos = 51,
    locus = "chr2:222,216,634 (hg38)",
    snp_id = "rs121434257 (PAX3)",
    phenotype = "Associated with sectoral heterochromia (Waardenburg Syndrome type 1).",
    color = "orchid"
  ),
  "Limbal/Pigmented Ring" = list(
    # rs4900109 (SLC24A4)
    seq = "GAGCATGAAATAGCTCCTGAACCCAAGAAAAATTTCATGTTCCAGTAGAAGGGCATTGATGACAAAGCCTGCTTCTGCCGTTTACTTGCTGGGGCTTTGGA",
    snp_pos = 52,
    locus = "chr14:92,297,047 (hg38)",
    snp_id = "rs4900109 (SLC24A4)",
    phenotype = "Associated with the presence and prominence of a pigmented ring in the iris.",
    color = "black"
  ),
  # Martin-Schultz Scale (1a-16)
  "1a: Pale Blue Iris" = list(
    # rs4778219 (HERC2)
    seq = "GAGCTCCAGGTGGCTGAGAGCGGGCAGCCACTTGGGCGAGGACGGGACTCAGCCCGCGGGTGCCCGGGGCGCAGGTGCAGGTGCCCGGCCGCCGCCGCC",
    snp_pos = 52,
    locus = "chr15:28,126,543 (hg38)",
    snp_id = "rs4778219 (HERC2)",
    phenotype = "Martin-Schultz Scale 1a: Pale blue iris (lightest).",
    color = "#ADD8E6"
  ),
  "1b: Light Blue Iris" = list(
    # rs8024968 (HERC2)
    seq = "CCTCAGACCTCATCACATGTGCCACTGAGCAGGGCGGTGGTGAGGGTGGGGACAGGGGCCTGGGTTGGGGTGGGGGTGTGGGGAGGCCAGGGACAGCCG",
    snp_pos = 52,
    locus = "chr15:28,132,567 (hg38)",
    snp_id = "rs8024968 (HERC2)",
    phenotype = "Martin-Schultz Scale 1b: Light blue iris.",
    color = "#87CEEB"
  ),
  "1c: Sky Blue Iris" = list(
    # rs7183877 (HERC2)
    seq = "GGGCGGTGGTGAGGGTGGGGACAGGGGCCTGGGTTGGGGTGGGGGTGTGGGGAGGCCAGGGACAGCCGGCAGCCTGGGGTGCGGGCGCGGGTGCAGG",
    snp_pos = 52,
    locus = "chr15:28,138,234 (hg38)",
    snp_id = "rs7183877 (HERC2)",
    phenotype = "Martin-Schultz Scale 1c: Sky blue iris.",
    color = "#87CEFA"
  ),
  "2a: Blue Iris" = list(
    # rs11638447 (HERC2)
    seq = "TGCGGGCGCGGGTGCAGGTGCAGGTGCCCGGCCGCCGCCGCCCGCCGCCCGCCGCGCTGCCCGAGGTGCGCCGAGCCTGCACCCCGGGGTGCGTGC",
    snp_pos = 52,
    locus = "chr15:28,144,891 (hg38)",
    snp_id = "rs11638447 (HERC2)",
    phenotype = "Martin-Schultz Scale 2a: Blue iris.",
    color = "#4169E1"
  ),
  "2b: Dark Blue Iris" = list(
    # rs3935591 (HERC2)
    seq = "CCCGCCGCGCTGCCCGAGGTGCGCCGAGCCTGCACCCCGGGGTGCGTGCGCGTGGGCGAGGGGCGGGACGCCCGGGACCCCGGCGAGCCTCGACGAG",
    snp_pos = 52,
    locus = "chr15:28,151,456 (hg38)",
    snp_id = "rs3935591 (HERC2)",
    phenotype = "Martin-Schultz Scale 2b: Dark blue iris.",
    color = "#0000CD"
  ),
  "3: Blue-Gray Iris" = list(
    # rs238538 (SLC24A4)
    seq = "CCCTGTGCTGCCTGTGTGCTTCTGTTGGATAGCATCTGACCCCGCCCCTGCCTCCCAGCCCCACCCGCCCCCAGGGGCAGCAGCTGACCTGACCTCACTG",
    snp_pos = 52,
    locus = "chr14:92,045,234 (hg38)",
    snp_id = "rs238538 (SLC24A4)",
    phenotype = "Martin-Schultz Scale 3: Blue-gray iris.",
    color = "#708090"
  ),
  "4a: Light Gray Iris" = list(
    # rs12896399 (SLC24A4) - lighter variant
    seq = "CATGCACCACCATGCCTGGCTAATTTTTGTTCTTTAGTAGAGATGGGGTTTTACCATATTGGCAAGGCTGGTCTCAAACTCCTGACCTCAAACAATCCACC",
    snp_pos = 52,
    locus = "chr14:92,113,279 (hg38)",
    snp_id = "rs12896399-T (SLC24A4)",
    phenotype = "Martin-Schultz Scale 4a: Light gray iris.",
    color = "#C0C0C0"
  ),
  "4b: Dark Gray Iris" = list(
    # rs12976356 (SLC24A4)
    seq = "GATGTGACAGATGACTGATCAGTGCCTGGCCAGGCTGGGCCAGGCTCCCAGGGGCTGGGCCCAGGCCCTCCTGGGCCCCAGCCCCACTGTGGGCCCAGGC",
    snp_pos = 52,
    locus = "chr14:92,156,789 (hg38)",
    snp_id = "rs12976356 (SLC24A4)",
    phenotype = "Martin-Schultz Scale 4b: Dark gray iris.",
    color = "#808080"
  ),
  "5: Blue-Gray with Yellow/Brown Spots" = list(
    # rs4778138 (HERC2)
    seq = "CCGGGCCGCGCACCTGCGCGGGCCGGGCCGGGCCCGGCCGCGCGGGGCCGGGGAGGGGCGCGCGTCCTGCCCTGCCGAGCCGCCCCCACCTGGACGCC",
    snp_pos = 52,
    locus = "chr15:28,090,674 (hg38)",
    snp_id = "rs4778138 (HERC2)",
    phenotype = "Martin-Schultz Scale 5: Blue-gray iris with yellow/brown spots.",
    color = "#9370DB"
  ),
  "6: Gray-Green with Yellow/Brown Spots" = list(
    # rs1126809 (TYR)
    seq = "GGGGCGGGGCCCGAGGGCCGGCGCAGCCCTGCCCGGCCTGCGGGGCCTGCAGGCCCGGGGCGGGCGCTGGGCTCGGGCCCGGGCGGGGCCCTGGCCCA",
    snp_pos = 52,
    locus = "chr11:89,284,793 (hg38)",
    snp_id = "rs1126809 (TYR)",
    phenotype = "Martin-Schultz Scale 6: Gray-green iris with yellow/brown spots.",
    color = "#66CDAA"
  ),
  "7: Green Iris" = list(
    # rs12203592 (IRF4) - strong green association
    seq = "TGATGTGAATGACAGCTTTGTTTCATCCACTTTGGTGGGTAAAAGAAGGCAAATTCCCCTGTGGTACTTTTGGTGCCAGGTTTAGCCATATGACGAAGCT",
    snp_pos = 51,
    locus = "chr6:396,321 (hg38)",
    snp_id = "rs12203592 (IRF4)",
    phenotype = "Martin-Schultz Scale 7: Green iris.",
    color = "#228B22"
  ),
  "8: Green with Yellow/Brown Spots" = list(
    # rs1393350 (TYRP1)
    seq = "TCCTGATGGACTCTAGGTAACTTACTCCTTTGCTTTCCAAAAGAGTAATAAGAAAAGCTATATTTAATTTAATGTGGTTCCATTTGTAGAGAGAAATAATA",
    snp_pos = 52,
    locus = "chr11:89,010,977 (hg38)",
    snp_id = "rs1393350-G (TYRP1)",
    phenotype = "Martin-Schultz Scale 8: Green iris with yellow/brown spots.",
    color = "#9ACD32"
  ),
  "9: Amber Iris" = list(
    # rs1540771 (ASIP)
    seq = "TGTAATCCCGGCACTTTGGGAGGCCGAGGTGGGCGGATCACGAGGTCAGGAGATCGAGACCATCTTGGCTAACATGGTGAAACCCCGTCTCTACTAAAAAT",
    snp_pos = 52,
    locus = "chr20:34,138,092 (hg38)",
    snp_id = "rs1540771 (ASIP)",
    phenotype = "Martin-Schultz Scale 9: Amber iris.",
    color = "#FFBF00"
  ),
  "10: Hazel Iris" = list(
    # rs1800407 (OCA2)
    seq = "GGACGGCCGCGATGAGACAGAGCATGATGATCATGGCCCACACCCGTCCCCGGGAGAGCCGGTATGCCTGGCCACACACACACAGAGAGAGTACAAGCCAG",
    snp_pos = 52,
    locus = "chr15:27,985,172 (hg38)",
    snp_id = "rs1800407 (OCA2)",
    phenotype = "Martin-Schultz Scale 10: Hazel iris.",
    color = "#8E7618"
  ),
  "11: Light Brown Iris" = list(
    # rs1667394 (HERC2)
    seq = "CCGCGCCCTCCCTGGCTGGAGCCTCCGGCCTCCGCCGCCCCCGCCTCCCCGGCGGCCCTGCGGTGGAGCCTGAGCCTGGCGCTCCCGGGACGGCCGCCGC",
    snp_pos = 52,
    locus = "chr15:28,285,036 (hg38)",
    snp_id = "rs1667394 (HERC2)",
    phenotype = "Martin-Schultz Scale 11: Light brown iris.",
    color = "#D2691E"
  ),
  "12: Medium Brown Iris" = list(
    # rs12194118 (OCA2)
    seq = "GACCCCCTCTCTGCCCTCCCACCCCGCTGACCCCAGCTCCCCTCTCCACCCTCACCCCCCTCCCTCCCTGCCCTCTCCCTCCCCAGCCCTGGGACCCCTGGC",
    snp_pos = 52,
    locus = "chr15:27,920,567 (hg38)",
    snp_id = "rs12194118 (OCA2)",
    phenotype = "Martin-Schultz Scale 12: Medium brown iris.",
    color = "#A0522D"
  ),
  "13: Dark Brown (Mahogany) Iris" = list(
    # rs1800401 (OCA2)
    seq = "CTGATGAGCCATCAAAAGAGGGACAGCCTGGGTCTGCTGCAGGGAGGCCCGGATGCTGATGGACACCGTCTCTCTGCAGAACGAAACAACGACCTTACTGT",
    snp_pos = 52,
    locus = "chr15:28,014,907 (hg38)",
    snp_id = "rs1800401 (OCA2)",
    phenotype = "Martin-Schultz Scale 13: Dark brown (mahogany) iris.",
    color = "#5C4033"
  ),
  "14: Brown-Black (Deep Brown) Iris" = list(
    # rs2238288 (IRF4)
    seq = "GGGCGCAGCCGCGGGGCGCTGGGGCCGCAGGTGCGGGCGCACTCCTGCCGCGCCCGGGGCCGGGGCCGGGCCCGGGCGGGGCGGGGCCGGGCCGGGC",
    snp_pos = 52,
    locus = "chr6:401,234 (hg38)",
    snp_id = "rs2238288 (IRF4)",
    phenotype = "Martin-Schultz Scale 14: Brown-black (deep brown) iris.",
    color = "#3D2B1F"
  ),
  "15: Black-Brown Iris" = list(
    # rs1695778 (SLC45A2)
    seq = "GGGCGGCGCGGGGTGCGGTGAGCAGCGTGGGGTCGGGGCGACAGCCCCGCGCGCACACAGCAGCCACTCGCGCACCCCCGAGCCCGAGCTGGCCGGGC",
    snp_pos = 52,
    locus = "chr5:33,968,567 (hg38)",
    snp_id = "rs1695778 (SLC45A2)",
    phenotype = "Martin-Schultz Scale 15: Black-brown iris.",
    color = "#1C1C1C"
  ),
  "16: Black Iris" = list(
    # rs12194118 combined with dark variants
    seq = "CCCCCCCGAGCCCGAGCTGGCCGGGCCGGGTCCGGGGTCGCACCCGCGCCTCGCAGCCAGCCGAGCCCGGGCCCGGACTCGGCGCTGGGTCGGGCGTGG",
    snp_pos = 52,
    locus = "chr15:27,890,123 (hg38)",
    snp_id = "rs12194118-AA (OCA2)",
    phenotype = "Martin-Schultz Scale 16: Black iris (darkest).",
    color = "#000000"
  )
)
