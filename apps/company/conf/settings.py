# LDAP connection settings
ldap = {
    'uri': 'ldap://example.com',
    'user_dn': 'uid=me,ou=people,dc=example,dc=com',
    'passwd': 'mypass',
    'ou_base': 'ou=units,dc=example,dc=com',
    'tls': False,
}

csv_defaults = {
    'encoding': 'iso8859-7',
    'delimiter': ';',
    'dry_run': True,
}

dbmaps = {
    # Αντιστοιχία Φορέων Υλοποίησης με company.departments
    # Βγαίνει αυτόματα από το ./manage.py import_depts_csv --limit 30 --fy-mode foreis\ ylopoihsh.csv
    # ΠΡΕΠΕΙ να ρυθμίζεται σε κάθε νέα βάση!
    'fy_id2dept': {
    }
}

#eof

