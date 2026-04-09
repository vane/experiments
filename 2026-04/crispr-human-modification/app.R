# CRISPR Eye Color Modification Template
library(shiny)
source("utils.R")

# Target locus: rs12913832 (HERC2/OCA2 enhancer)
# Location: hg38 chr15:28,120,472
# Alleles: A (Brown) / G (Blue)
target_sequence <- "TGTCTACCCTAAACATGTTCACAGGGTGAGCCACCTGGGCAGAATTAGAGAGTGACATCTTCCCTCAGCCCCAGTCTCTACTCCTACTTCCACCACTCCACCTTAATCTCTCA"
snp_pos <- 52 # SNP at pos 52

# UI definition
ui <- fluidPage(
  theme = bslib::bs_theme(version = 5, bootswatch = "cosmo"),
  titlePanel("CRISPR Eye Color Modification Template"),
  
  sidebarLayout(
    sidebarPanel(
      h4("Configuration"),
      helpText("Design CRISPR guides for rs12913832 locus."),
      selectInput("target_allele", "Target Allele:", choices = c("A (Brown)", "G (Blue)")),
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
                 p("Locus: chr15:28,120,472 (hg38)"),
                 hr(),
                 h4("Genetic Info"),
                 p("This SNP is located in the HERC2 gene but regulates OCA2 expression. 
                   Modifying it can switch eye color phenotype.")
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
  
  results <- reactiveValues(guides = NULL)
  
  observeEvent(input$design, {
    # Use improved design function from utils.R
    df <- design_guides(target_sequence, guide_len = input$guide_len)
    
    if (nrow(df) > 0) {
      df$SNP_Targeted <- sapply(1:nrow(df), function(i) {
        is_snp_targeted(df$Start[i], df$End[i], snp_pos)
      })
    }
    results$guides <- df
  })
  
  output$seq_display <- renderUI({
    # Highlight SNP
    part1 <- substr(target_sequence, 1, snp_pos - 1)
    snp <- substr(target_sequence, snp_pos, snp_pos)
    part2 <- substr(target_sequence, snp_pos + 1, nchar(target_sequence))
    
    HTML(paste0("<pre style='font-family: monospace;'>", 
                part1, "<span style='color: red; font-weight: bold;'>[", snp, "]</span>", part2, 
                "</pre>"))
  })
  
  output$guide_table <- renderTable({
    req(results$guides)
    results$guides
  })
}

shinyApp(ui = ui, server = server)
