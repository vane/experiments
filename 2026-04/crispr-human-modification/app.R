# CRISPR Eye Color Modification Template
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
  "Green" = list(
    # rs12203592 (IRF4)
    seq = "TGATGTGAATGACAGCTTTGTTTCATCCACTTTGGTGGGTAAAAGAAGGCAAATTCCCCTGTGGTACTTTTGGTGCCAGGTTTAGCCATATGACGAAGCT",
    snp_pos = 51,
    locus = "chr6:396,321 (hg38)",
    snp_id = "rs12203592 (IRF4)",
    phenotype = "Associated with intermediate (Green/Hazel) eye color."
  ),
  "Red" = list(
    # rs1042602 (TYR)
    seq = "AACAAACACAAAAATAGACAAATAGGATTACTTCAAACTAAAAATCTCCAAGCGACCAAGAAAACAATTAACATGATAGACAGACAACTTACACAATAGG",
    snp_pos = 51,
    locus = "chr11:89,230,557 (hg38)",
    snp_id = "rs1042602 (TYR)",
    phenotype = "Associated with oculocutaneous albinism (Reddish/Pink eyes)."
  )
)

# UI definition
ui <- fluidPage(
  theme = bslib::bs_theme(version = 5, bootswatch = "cosmo"),
  titlePanel("CRISPR Eye Color Modification Template"),
  
  sidebarLayout(
    sidebarPanel(
      h4("Configuration"),
      helpText("Design CRISPR guides for phenotypic eye color modification."),
      selectInput("target_color", "Desired Modification:", 
                  choices = c("Brown/Blue", "Green", "Red")),
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
    targets[[input$target_color]]
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
    display_color <- switch(input$target_color,
                            "Brown/Blue" = "brown",
                            "Green" = "green",
                            "Red" = "red")
    
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
