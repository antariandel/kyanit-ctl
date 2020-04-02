import os
import sys
import pdoc


PACKAGE_NAME = 'kyanitctl'
DOCS_DIR = 'docs'
PYTHONPATHS = []


for path in PYTHONPATHS:
    sys.path.append(os.path.join(os.getcwd(), path))

context = pdoc.Context()
package = pdoc.Module(PACKAGE_NAME, context=context)
pdoc.link_inheritance(context)
pdoc.tpl_lookup.directories.insert(0, os.path.join(DOCS_DIR, 'templates'))

docs_dir_htmls = [file for file in os.listdir(DOCS_DIR)
                  if os.path.isfile(file) and file.endswidth('.html')]


def recursive_htmls(mod):
    yield mod.name, mod.html()
    for submod in mod.submodules():
        yield from recursive_htmls(submod)


for module_name, html in recursive_htmls(package):
    if module_name == PACKAGE_NAME:
        filename = 'index.html'
    else:
        filename = '{}.html'.format(module_name.rpartition('.')[2])
    with open(os.path.join(DOCS_DIR, filename), 'w') as file:
        file.write(html)
    if filename in docs_dir_htmls:
        docs_dir_htmls.remove(filename)

# delete leftovers:
for filename in docs_dir_htmls:
    os.remove(os.path.join(DOCS_DIR, filename))
