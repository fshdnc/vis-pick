#!/usr/bin/env python3

import re

sanitize_re=re.compile(r"[^a-zäöåA-ZÄÖÅ0-9 ]")
#whitespace_re=re.compile(r"\s+")
#suspicious_chars=re.compile("[lL1äaöo]")

def sanitize(txt):
    txt_clean=sanitize_re.sub("",txt) #remove weird characters and punctuation
    #txt_clean=suspicious_chars.sub("",txt_clean) #remove lL1 which get OCR-destroyed anyway
    #txt_clean=whitespace_re.sub(" ",txt_clean) #replace all whitespace with a single space
    return txt_clean.strip().lower() #strip and lowercase

def process_txt(text):
    """
    In the pick-ann tool, the text is processed before shown
    This function replicates the processing

    Details of the processing:
    https://github.com/TurkuNLP/pick-para-anno/blob/master/paraanno/app.py
    In function `fetch_document`
    """
    text = re.sub(r"\n+","\n",text)
    text = text.replace("<i>"," ").replace("</i>"," ")
    text = re.sub(r" +"," ",text)
    return text

def post_processing_txt(text):
    """
    In the pick-ann tool, the selected span is processed before saving
    This function replicates the processing

    Details of the processing:
    https://github.com/TurkuNLP/pick-para-anno/blob/master/paraanno/templates/doc.html
    `text = selection.toString().replace(/[\r\n]+/g," ");`
    """
    text = re.sub(r"[\n\r]", " ", text)
    return text

def map_processed_text(before, after):
    """
    Takes a piece of text before and after processing,
    and return a map of where the individual character is before processing

    Input
        before: string
        after: string
    
    Output
        Dict {index_after_processing: index_before_processing}
    """
    mapping = {}
    i_a = 0 # index count for `after`
    MOVED = False
    end = len(after)
    for i_b, c_b in enumerate(before):
        #print(i_a,i_b,after[i_a],c_b,MOVED)
        if c_b == after[i_a]:
            mapping[i_a] = i_b
            i_a += 1
            MOVED = False
        else:
            #assert c_b in ["\n","\r","<","i",">","/"," "] # the character was replaced/deleted
            if after[i_a] == " " and not MOVED: # move the index at `after` by one
                mapping[i_a] = i_b
                i_a += 1
                MOVED = True
        if i_a == end:
            break
    return mapping

#def locate_segment_in_original_text(segment, after, mapping):
def INDEX_locate_segment_in_original_text(segment, after, mapping):
    """
    Search for where the segment of text locates in the text before processing
    """
    try:
        a_start = after.index(segment)
        a_end = a_start + len(segment)
        return (mapping[a_start], mapping[a_end-1]+1)
    except ValueError:
        return (0, 0)

def locate_segment_in_original_text(segment, after, mapping):
    """
    Search for where the segment of text locates in the text before processing
    """
    segment = sanitize(segment)
    a_start = after.find(segment)
    a_end = a_start + len(segment)
    #if a_start == -1:
        # if the annotator truncates the original sentence
        # e.g. Minullla on älyttömästi asioita hoidettavana ennen keikkaa eikä...
        #   -> Minullla on älyttömästi asioita hoidettavana.
    #    segment = segment[:-1].lower()
    #    a_start = after.lower().find(segment)
    #    a_end = a_start + len(segment)
    if a_start == -1:
        return (0,0)
    else:
        try:
            return (mapping[a_start], mapping[a_end]-mapping[a_start]) # start, len
        except KeyError:
            return (1,1)
