# set ROOT_DIR to path to directory that contains s2e.py
ROOT_DIR         = ~/Documents/NaMaBooks/scriv2epub
S2E              = $(ROOT_DIR)/s2e.py
MAKE_EPUB        = ~/bin/mkep
TMPL_DIR         = $(ROOT_DIR)/tmpl
SRC_DIR          = src
STATIC_SOURCES   = ./src/*.xhtml
MD_SOURCES       = ./src/*.md
STYLE_SHEET      = ./OPS/css/stylesheet.css
IMG_DIR          = ./OPS/img
HTML_DIR         = OPS
# $(MARKDOWN_COOKIE) will be dependent of RTF sources and triggers
# re-generation of *.md files in case any RTF is newer than $(MARKDOWN_COOKIE)
MARKDOWN_COOKIE  = markdown.timestamp
# OPF used as indicator for freshly generated contents
OPF              = ./OPS/content.opf

# overwrite by assigning on cmd line or edit below if desired
BOOK             = desert_hunt
META_YAML        = ./meta.yaml
MM_YAML          = ./mainmatter.yaml
HOFFSET          = 1
YINCL            = ~/Documents/NaMaBooks/annalowebooks.com/yaml
SCRIV_ROOT       = ./$(BOOK).scriv
SCRIV_XML        = project.scrivx
SCRIV_RTF        = Files/Docs
EXCLUDE_LIST     = ./exclude.list


.PHONY: help
help:
	@echo
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  info     to display variable values"
	@echo "  epub     to generate EPUB and MOBI files"
	@echo "  content  to generate EPUB content and metadata from YAML config"
	@echo "           files and md/xhtml sources"
	@echo "  markdown to generate Markdown mainmatter files from RTF sources"
	@echo "  mmyaml   to generate the mainmatter page inventory"
	@echo

.PHONY: info
info:
	@echo
	@echo 'Running make with these variable settings'
	@echo '-----------------------------------------'
	@echo 'ROOT_DIR        : '$(ROOT_DIR)
	@echo 'S2E             : '$(S2E)
	@echo 'MAKE_EPUB       : '$(MAKE_EPUB)
	@echo 'TMPL_DIR        : '$(TMPL_DIR)
	@echo 'STYLE_SHEET     : '$(STYLE_SHEET)
	@echo 'IMG_DIR         : '$(IMG_DIR)
	@echo 'OPF             : '$(OPF)
	@echo 'SRC_DIR         : '$(SRC_DIR)
	@echo 'HTML_DIR        : '$(HTML_DIR)
	@echo 'MARKDOWN_COOKIE : '$(HTML_DIR)
	@echo
	@echo 'BOOK            : '$(BOOK)
	@echo 'META_YAML       : '$(META_YAML)
	@echo 'MM_YAML         : '$(MM_YAML)
	@echo 'HOFFSET         : '$(HOFFSET)
	@echo 'YINCL           : '$(YINCL)
	@echo 'SCRIV_ROOT      : '$(SCRIV_PROJ_ROOT)
	@echo 'SCRIV_RTF       : '$(SCRIV_RTF)
	@echo 'SCRIV_XML       : '$(SCRIV_XML)
	@echo 'EXCLUDE_LIST    : '$(EXCLUDE_LIST)
	@echo


.PHONY: epub
epub: info
	$(MAKE_EPUB) $(BOOK) $(EXCLUDE_LIST)

.PHONY: content
content: info
	$(S2E) genep --metayaml $(META_YAML) --mmyaml $(MM_YAML) --yincl $(YINCL) \
		--imgdir $(IMG_DIR) --htmldir $(HTML_DIR) --srcdir $(SRC_DIR)

.PHONY: markdown
markdown: info $(MARKDOWN_COOKIE)
$(MARKDOWN_COOKIE):
	$(S2E) scriv2md --mmyaml $(MM_YAML) --mddir $(SRC_DIR) \
		--projdir $(SCRIV_ROOT)
	touch $(MARKDOWN_COOKIE)

.PHONY: mmyaml
mmyaml: $(MM_YAML)
$(MM_YAML):
	$(S2E) scrivx2yaml --projdir $(SCRIV_ROOT) --rtfdir $(SCRIV_RTF) \
		--output $(MM_YAML) --typefilter 'Text' --headings --type 'chapter' \
		--toptitle 'Manuscript' --hoffset $(HOFFSET)
