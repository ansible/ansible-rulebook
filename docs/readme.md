# Some tips for documentation development

- Ensure your dependencies

```
pip install -r requirements_dev.txt
```

- Simulate a hot-reload web server

```
# install when-changed
pip install git+https://github.com/joh/when-changed

# rebuild with every change
cd docs
when-changed . -c "make clean && make html"

# spin up a basic http server
cd _build/html
python -m http.server 3000

# or install sphinx-autobuild
pip install sphinx-autobuild

# monitor it and auto-rebuild with every change
sphinx-autobuild docs _build/html --port 3000
```

- nice RST extension for vscode:
<https://marketplace.visualstudio.com/items?itemName=trond-snekvik.simple-rst>

## Some useful links

- <https://bashtage.github.io/sphinx-material/rst-cheatsheet/rst-cheatsheet.html>
- <https://github.com/ralsina/rst-cheatsheet/blob/master/rst-cheatsheet.rst>
- <https://docs.generic-mapping-tools.org/6.2/rst-cheatsheet.html>
- <https://sublime-and-sphinx-guide.readthedocs.io/en/latest/tables.html>
- <https://docutils.sourceforge.io/docs/user/rst/quickref.html>
- <https://thomas-cokelaer.info/tutorials/sphinx/rest_syntax.html>
- <https://restructuredtext.documatt.com/>
- <https://hyperpolyglot.org/lightweight-markup>
