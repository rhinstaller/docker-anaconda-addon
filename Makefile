PKGNAME=docker-anaconda-addon
ADDONNAME=com_redhat_docker
VERSION=$(shell awk '/Version:/ { print $$2 }' $(PKGNAME).spec)
ADDONDIR=/usr/share/anaconda/addons/
PYTHONPATH=.

ZANATA_PULL_ARGS = --transdir po/
ZANATA_PUSH_ARGS = --srcdir po/ --push-type source --force

check:
	@echo "*** Running pylint to verify source ***"
	tests/pylint/runpylint.py

clean:
	-rm pylint-log updates.img
	-rm -rf updates
	-rm -rf docs/html.new

install:
	mkdir -p $(DESTDIR)$(ADDONDIR)
	cp -rv $(ADDONNAME) $(DESTDIR)$(ADDONDIR)
	$(MAKE) install-po-files

tag:
	git tag -s -a -m "Tag as $(VERSION)" -f $(VERSION)
	@echo "Tagged as $(VERSION)"

release: po-pull check tag
	git archive --format=tar --prefix=$(PKGNAME)-$(VERSION)/ $(VERSION) > $(PKGNAME)-$(VERSION).tar
	mkdir $(PKGNAME)-$(VERSION)
	cp -r po $(PKGNAME)-$(VERSION)
	tar -rf $(PKGNAME)-$(VERSION).tar $(PKGNAME)-$(VERSION)
	gzip -9 $(PKGNAME)-$(VERSION).tar
	rm -rf $(PKGNAME)-$(VERSION)
	git checkout -- po/$(PKGNAME).pot
	@echo "The archive is in $(PKGNAME)-$(VERSION).tar.gz"

scratch: po-pull check
	git archive --format=tar --prefix=$(PKGNAME)-$(VERSION)/ HEAD > $(PKGNAME)-$(VERSION).tar
	mkdir $(PKGNAME)-$(VERSION)
	cp -r po $(PKGNAME)-$(VERSION)
	tar -rf $(PKGNAME)-$(VERSION).tar $(PKGNAME)-$(VERSION)
	gzip -9 $(PKGNAME)-$(VERSION).tar
	rm -rf $(PKGNAME)-$(VERSION)
	git checkout -- po/$(PKGNAME).pot
	@echo "The archive is in $(PKGNAME)-$(VERSION).tar.gz"

rpmlog:
	@git log --pretty="format:- %s (%ae)" $(VERSION).. |sed -e 's/@.*)/)/' | grep -v "Merge pull request"

bumpver: po-pull
	@NEWSUBVER=$$((`echo $(VERSION) |cut -d . -f 2` + 1)) ; \
	NEWVERSION=`echo $(VERSION).$$NEWSUBVER |cut -d . -f 1,3` ; \
	DATELINE="* `date "+%a %b %d %Y"` `git config user.name` <`git config user.email`> - $$NEWVERSION-1"  ; \
	cl=`grep -n %changelog ${PKGNAME}.spec |cut -d : -f 1` ; \
	tail --lines=+$$(($$cl + 1)) ${PKGNAME}.spec > speclog ; \
	(head -n $$cl ${PKGNAME}.spec ; echo "$$DATELINE" ; make --quiet rpmlog 2>/dev/null ; echo ""; cat speclog) > ${PKGNAME}.spec.new ; \
	mv ${PKGNAME}.spec.new ${PKGNAME}.spec ; rm -f speclog ; \
	sed -i "s/Version:   $(VERSION)/Version:   $$NEWVERSION/" ${PKGNAME}.spec

ci:
	PYTHONPATH=. tests/pylint/runpylint.py

potfile:
	$(MAKE) DESTDIR=$(DESTDIR) -C po potfile

po-pull:
	rpm -q zanata-python-client &>/dev/null || ( echo "need to run: dnf install zanata-python-client"; exit 1 )
	zanata pull $(ZANATA_PULL_ARGS)

push-pot: potfile
	zanata push $(ZANATA_PUSH_ARGS)

install-po-files:
	$(MAKE) -C po install

.PHONY: check clean install tag release
