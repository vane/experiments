# Utility functions for CRISPR design using Bioconductor libraries

#' Find potential gRNAs for a given sequence
#' @param sequence A DNAString or character string
#' @param pam The PAM sequence (default NGG)
#' @param guide_len Length of the guide (default 20)
#' @return A data.frame with guide coordinates and sequences
design_guides <- function(sequence, pam = "NGG", guide_len = 20) {
  # Load Biostrings only when needed
  if (!requireNamespace("Biostrings", quietly = TRUE)) {
    stop("Biostrings package required. Install using BiocManager::install('Biostrings')")
  }
  
  dna_seq <- Biostrings::DNAString(sequence)
  
  # 1. Forward Strand Analysis (search for NGG)
  matches_fwd <- Biostrings::matchPattern(pam, dna_seq, fixed = FALSE)
  fwd_guides <- data.frame(
    Start = IRanges::start(matches_fwd) - guide_len,
    End = IRanges::end(matches_fwd),
    Strand = rep("+", length(matches_fwd)),
    stringsAsFactors = FALSE
  )
  
  # Filter valid fwd guides
  fwd_guides <- fwd_guides[fwd_guides$Start > 0, ]
  if (nrow(fwd_guides) > 0) {
    fwd_guides$Sequence <- sapply(1:nrow(fwd_guides), function(i) {
      as.character(Biostrings::subseq(dna_seq, fwd_guides$Start[i], fwd_guides$End[i]))
    })
  }
  
  # 2. Reverse Strand Analysis (search for CCN on forward strand)
  # PAM is CCN on forward => NGG on reverse
  pam_rev <- as.character(Biostrings::reverseComplement(Biostrings::DNAString(pam)))
  matches_rev <- Biostrings::matchPattern(pam_rev, dna_seq, fixed = FALSE)
  
  rev_guides <- data.frame(
    Start = IRanges::start(matches_rev),
    End = IRanges::end(matches_rev) + guide_len,
    Strand = rep("-", length(matches_rev)),
    stringsAsFactors = FALSE
  )
  
  # Filter valid rev guides
  rev_guides <- rev_guides[rev_guides$End <= Biostrings::nchar(dna_seq), ]
  if (nrow(rev_guides) > 0) {
    rev_guides$Sequence <- sapply(1:nrow(rev_guides), function(i) {
      # Extract forward seq and RC it to get guide + PAM sequence
      # PAM is at the end of the guide (on the reverse strand)
      # PAM on rev corresponds to first 3 chars on forward sequence
      # So guide sequence on rev is at the end of extracted chunk
      as.character(Biostrings::reverseComplement(Biostrings::subseq(dna_seq, rev_guides$Start[i], rev_guides$End[i])))
    })
  }
  
  return(rbind(fwd_guides, rev_guides))
}

#' Check if an SNP is targeted by a guide
#' @param guide_start Start position of the guide
#' @param guide_end End position of the guide (including PAM)
#' @param snp_pos Position of the SNP
#' @return Boolean
is_snp_targeted <- function(guide_start, guide_end, snp_pos) {
  return(snp_pos >= guide_start && snp_pos <= guide_end)
}
