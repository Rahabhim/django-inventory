Django Inventory
=============

Django based inventory and asset control.
Heavily modified and adapted to Hellenic School network http://www.sch.gr

 
![screenshot](http://img814.imageshack.us/img814/5088/screenshot1fz.png)
![screenshot2](http://img443.imageshack.us/img443/1486/screenshot2wu.png)


Features
---

* Object oriented approach to asset and inventory management.
* Double-ledger system, full traceability of assets
* Department/Location structure of storage
* Procurement wizard, guide the user to enter Purchase Orders
* LDAP, CAS2 integration
* Locking inventories, which prohibit modifications on earlier dates
* An item can be defined as a supply to another item.
* Assign assets to one or more individuals.
* Online documentation system for any screen/entity
* Flexible reporting system, with Cube-like functionality


Requirements
---

* Django - A high-level Python Web framework that encourages rapid development and clean, pragmatic design.
* PIL - The Python Imaging Library.
* django-pagination
* django-photologue - Powerful image management for the Django web framework.

Or execute pip install -r requirements/production.txt to install the dependencies automatically.


Installation
---

Check the INSTALL file in the docs folder
or if you are brave, copy the file [install.sh](https://github.com/rosarior/django-inventory/blob/master/misc/install.sh) file to your computer and execute it.
This script has only been tested under Ubuntu/Maverick/amd64 w/ Apache2 & bash, revise it before running it.


Author
------

Roberto Rosario - [Twitter](http://twitter.com/#siloraptor) [E-mail](roberto.rosario.gonzalez at gmail)
Panos Christeas - [E-Mail](xrg at linux.gr)



[![Bitdeli Badge](https://d2weczhvl823v0.cloudfront.net/rosarior/django-inventory/trend.png)](https://bitdeli.com/free "Bitdeli Badge")

