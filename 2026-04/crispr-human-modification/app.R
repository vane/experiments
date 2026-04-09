# CRISPR Genomic Modification Template
library(shiny)
source("utils.R")

# Target configurations
targets <- list(
  "Brown/Blue" = list(
    seq = "TGTCTACCCTAAACATGTTCACAGGGTGAGCCACCTGGGCAGAATTAGAGAGTGACATCTTCCCTCAGCCCCAGTCTCTACTCCTACTTCCACCACTCCACCTTAATCTCTCA",
    snp_pos = 52,
    locus = "chr15:28,120,472 (hg38)",
    snp_id = "rs12913832 (HERC2/OCA2)",
    phenotype = "Major determinant of eye color (Brown/Blue)."
  ),
  "Dark Brown" = list(
    # rs1800401 (OCA2)
    seq = "CTGATGAGCCATCAAAAGAGGGACAGCCTGGGTCTGCTGCAGGGAGGCCCGGATGCTGATGGACACCGTCTCTCTGCAGAACGAAACAACGACCTTACTGT",
    snp_pos = 52,
    locus = "chr15:28,014,907 (hg38)",
    snp_id = "rs1800401 (OCA2)",
    phenotype = "Associated with deep brown pigmentation."
  ),
  "Green" = list(
    # rs12203592 (IRF4)
    seq = "TGATGTGAATGACAGCTTTGTTTCATCCACTTTGGTGGGTAAAAGAAGGCAAATTCCCCTGTGGTACTTTTGGTGCCAGGTTTAGCCATATGACGAAGCT",
    snp_pos = 51,
    locus = "chr6:396,321 (hg38)",
    snp_id = "rs12203592 (IRF4)",
    phenotype = "Associated with intermediate (Green/Hazel) eye color."
  ),
  "Hazel" = list(
    # rs1800407 (OCA2)
    seq = "GGACGGCCGCGATGAGACAGAGCATGATGATCATGGCCCACACCCGTCCCCGGGAGAGCCGGTATGCCTGGCCACACACACACAGAGAGAGTACAAGCCAG",
    snp_pos = 52,
    locus = "chr15:27,985,172 (hg38)",
    snp_id = "rs1800407 (OCA2)",
    phenotype = "Associated with green/hazel eye color variations."
  ),
  "Amber" = list(
    # rs1540771 (ASIP)
    seq = "TGTAATCCCGGCACTTTGGGAGGCCGAGGTGGGCGGATCACGAGGTCAGGAGATCGAGACCATCTTGGCTAACATGGTGAAACCCCGTCTCTACTAAAAAT",
    snp_pos = 52,
    locus = "chr20:34,138,092 (hg38)",
    snp_id = "rs1540771 (ASIP)",
    phenotype = "Associated with golden/amber eye color."
  ),
  "Grey" = list(
    # rs12896399 (SLC24A4)
    seq = "CATGCACCACCATGCCTGGCTAATTTTTGTTCTTTAGTAGAGATGGGGTTTTACCATATTGGCAAGGCTGGTCTCAAACTCCTGACCTCAAACAATCCACC",
    snp_pos = 52,
    locus = "chr14:92,113,279 (hg38)",
    snp_id = "rs12896399 (SLC24A4)",
    phenotype = "Associated with blue/grey eye color and blonde hair."
  ),
  "Light Blue" = list(
    # rs16891982 (SLC45A2)
    seq = "TAGACCAGAAACTTTTAGAAGACATCCTTAGGAGAGAGAAAGACTTACAAGAATAAAGTGAGGAAAACACGGAGTTGATGCACAAGCCCCAACATCCAACC",
    snp_pos = 52,
    locus = "chr5:33,951,556 (hg38)",
    snp_id = "rs16891982 (SLC45A2)",
    phenotype = "Common variant predicting light iris color."
  ),
  "Blue/Green" = list(
    # rs1393350 (TYRP1 locus area)
    seq = "TCCTGATGGACTCTAGGTAACTTACTCCTTTGCTTTCCAAAAGAGTAATAAGAAAAGCTATATTTAATTTAATGTGGTTCCATTTGTAGAGAGAAATAATA",
    snp_pos = 52,
    locus = "chr11:89,010,977 (hg38)",
    snp_id = "rs1393350 (near TYRP1)",
    phenotype = "Associated with blue/green eye color variations."
  ),
  "Red" = list(
    # rs1042602 (TYR)
    seq = "AACAAACACAAAAATAGACAAATAGGATTACTTCAAACTAAAAATCTCCAAGCGACCAAGAAAACAATTAACATGATAGACAGACAACTTACACAATAGG",
    snp_pos = 51,
    locus = "chr11:89,230,557 (hg38)",
    snp_id = "rs1042602 (TYR)",
    phenotype = "Associated with oculocutaneous albinism (Reddish/Pink eyes)."
  ),
  # Nose targets
  "Nose Wing Breadth" = list(
    seq = "ATCTCTTTATGGGTGCTCTTCAGGGGTATCTTTTCAGGGTTCTTGGTCAGCTGGTAAGTGTTACAATAATATCTCTTTTGAATATGTAACTATTATGCATT",
    snp_pos = 52,
    locus = "chr20:22,060,939 (hg38)",
    snp_id = "rs927833 (PAX1)",
    phenotype = "Associated with nose wing breadth."
  ),
  "Nose Protrusion" = list(
    seq = "GCTTATCACCAACTTTATGAAACTTACTGACTCTAAGTAGAGAACGAGCCGGTCAGGTTTCAAGTTTTTCTTAAATGTCAATATTCTAAAAAAGAAAGCTG",
    snp_pos = 52,
    locus = "chr4:153,910,747 (hg38)",
    snp_id = "rs2045323 (DCHS2)",
    phenotype = "Associated with nose protrusion and tip angle."
  ),
  "Columella Inclination" = list(
    seq = "TCAGCAATAAGTTCAGTATATGTCTATATACTTTGGGAAGTAGTTTTTGCATTGCTCAGCACCCTGTATTGCTCTGTTTCTACAGAGAACACTCTAAGAGA",
    snp_pos = 52,
    locus = "chr4:154,314,240 (hg38)",
    snp_id = "rs12644248 (DCHS2)",
    phenotype = "Associated with the angle of the columella (base of the nose)."
  ),
  "Nose Width" = list(
    seq = "TGCTACTCCTGATCTCTGCCTCCCAGCAGCTTCTGTCTAGCCTGCTGTCACCAGTCATGGGTTGGGATGGCCCTCTGTGTCTCAACGCAAAGGCCACACTT",
    snp_pos = 52,
    locus = "chr20:4,863,948 (hg38)",
    snp_id = "rs2206437 (DHX35)",
    phenotype = "Associated with wider and lower nose morphology."
  ),
  "Nose Length" = list(
    seq = "CTCTGGCCTGCCTTGCAGCCTTCGTGTATGAGCCCCGGTCTCACCCCAGGGTGCACCGGGCGCTCCTGTCCACCCCACCCCCGCAGCCCACTGGGCCGGGT",
    snp_pos = 52,
    locus = "chr1:116,167,664 (hg38)",
    snp_id = "rs647711 (IGSF3)",
    phenotype = "Associated with nasal length and general nose size."
  )
)

# Organize choices for UI
choice_list <- list(
  "Eye Color" = c("Brown/Blue", "Dark Brown", "Green", "Hazel", "Amber", "Grey", "Light Blue", "Blue/Green", "Red"),
  "Nose Size/Shape" = c("Nose Wing Breadth", "Nose Protrusion", "Columella Inclination", "Nose Width", "Nose Length")
)

# UI definition
ui <- fluidPage(
  theme = bslib::bs_theme(version = 5, bootswatch = "cosmo"),
  titlePanel("CRISPR Genomic Modification Template"),
  
  sidebarLayout(
    sidebarPanel(
      h4("Configuration"),
      helpText("Design CRISPR guides for phenotypic trait modification."),
      selectInput("target_trait", "Desired Modification:", 
                  choices = choice_list),
      hr(),
      sliderInput("guide_len", "Guide Length:", min = 15, max = 25, value = 20),
      actionButton("design", "Run Design", class = "btn-primary w-100"),
      br(), br(),
      if (!requireNamespace("Biostrings", quietly = TRUE)) {
        div(class = "alert alert-warning", 
            "Bioconductor libraries (Biostrings) not found. Please install using BiocManager.")
      }
    ),
    
    mainPanel(
      tabsetPanel(
        tabPanel("Genomics", 
                 h3("Target Sequence Context"),
                 uiOutput("seq_display"),
                 uiOutput("locus_info"),
                 hr(),
                 h4("Genetic Info"),
                 uiOutput("phenotype_info")
        ),
        tabPanel("CRISPR Design",
                 h3("Potential Guide RNAs"),
                 p("Searching for NGG PAM sites..."),
                 tableOutput("guide_table")
        ),
        tabPanel("Resources",
                 h3("Learning Materials"),
                 tags$ul(
                   tags$li(a(href="https://bioconductor.org/packages/Biostrings", "Biostrings Documentation")),
                   tags$li(a(href="https://bioconductor.org/packages/crisprDesign", "crisprDesign Package")),
                   tags$li(a(href="https://www.nature.com/articles/nmeth.3115", "Bioconductor for CRISPR research"))
                 )
        )
      )
    )
  )
)

# Server logic
server <- function(input, output) {
  
  # Reactive target based on selection
  current_target <- reactive({
    targets[[input$target_trait]]
  })
  
  results <- reactiveValues(guides = NULL)
  
  observeEvent(input$design, {
    target <- current_target()
    # Use improved design function from utils.R
    df <- design_guides(target$seq, guide_len = input$guide_len)
    
    if (nrow(df) > 0) {
      df$SNP_Targeted <- sapply(1:nrow(df), function(i) {
        is_snp_targeted(df$Start[i], df$End[i], target$snp_pos)
      })
    }
    results$guides <- df
  })
  
  output$seq_display <- renderUI({
    target <- current_target()
    # Highlight SNP with relevant color
    display_color <- switch(input$target_trait,
                            "Brown/Blue" = "brown",
                            "Dark Brown" = "#5C4033",
                            "Green" = "green",
                            "Hazel" = "#8E7618",
                            "Amber" = "#FFBF00",
                            "Grey" = "grey",
                            "Light Blue" = "lightblue",
                            "Blue/Green" = "cyan",
                            "Red" = "red",
                            "Nose Wing Breadth" = "purple",
                            "Nose Protrusion" = "purple",
                            "Columella Inclination" = "purple",
                            "Nose Width" = "purple",
                            "Nose Length" = "purple",
                            "black")
    
    part1 <- substr(target$seq, 1, target$snp_pos - 1)
    snp <- substr(target$seq, target$snp_pos, target$snp_pos)
    part2 <- substr(target$seq, target$snp_pos + 1, nchar(target$seq))
    
    HTML(paste0("<pre style='font-family: monospace;'>", 
                part1, "<span style='color: ", display_color, "; font-weight: bold;'>[", snp, "]</span>", part2, 
                "</pre>"))
  })
  
  output$locus_info <- renderUI({
    target <- current_target()
    p(strong("Locus: "), target$locus, br(),
      strong("SNP: "), target$snp_id)
  })
  
  output$phenotype_info <- renderUI({
    p(current_target()$phenotype)
  })
  
  output$guide_table <- renderTable({
    req(results$guides)
    results$guides
  })
}

shinyApp(ui = ui, server = server)
