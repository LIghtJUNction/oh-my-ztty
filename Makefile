.PHONY: check bundle bump
check:
	sh -n install.sh uninstall.sh bin/omztty bin/omztty-config bin/zshard
	for completion in packaging/completions/*; do zsh -n "$$completion" || exit; done
	python3 -m unittest discover -s tests -v
	python3 -m py_compile scripts/workspace.py scripts/build_bundle.py scripts/bump.py scripts/smoke_bundle.py scripts/publish_release.py scripts/verify_graphical.py

bundle:
	python3 scripts/build_bundle.py

bump:
	python3 scripts/bump.py $(or $(PART),patch)
