# Python tools for KiCad document batch processing

## Description

This python scripts are design to allow for automated update of KiCad schematics

The idea is that you could do mass update of several aspects of the document, like adding new fields to components of updating existing ones.

I've implemented support for an external database of components to be used as data source for automated field population. When making the schematic, you just set the Part Number for each component and then this script will add auxiliary fields from the Data Base automatically.


