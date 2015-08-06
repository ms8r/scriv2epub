#!/usr/bin/env bash
#
# md2htsnip: converts mardown files to html snippets and inserts css class
# into p tags
#


if [ $# != "1" ]
then
    echo
    echo "::::::::::::::::::::::::::::::::::::::::::::::::::::"
	echo "md2htsnip: convert markdown to HTML snippts"
	echo "usage: md2htsnip <directory>"
    echo "::::::::::::::::::::::::::::::::::::::::::::::::::::"
    echo
    exit 1
fi

css_basic=par-indent
css_center=center-par-tb-space
center_pattern="\&lt;\&lt;\&lt;\&gt;\&gt;\&gt;"   # paragraphs matching this
                                                  # pattern will be styled 
                                                  # with css_center

for mdf in $(ls -d $1/*.md)
do
    pandoc -f markdown -t html $mdf | \
        # replace line breaks by paragraph breaks
        sed "s/<br[ ]*\/>/<\/p>\n<p>/g" | \
        # tag <<<>>> as center-par
        sed "s/<p>[ ]*\($center_pattern[^<]*\)<\/p>/<p class=\"$css_center\">\1<\/p>/g" | \
        # tag everything else as basic indented paragraph
        sed "s/<p>/<p class=\"$css_basic\">/g" > ${mdf%.md}.htsnippet
done
