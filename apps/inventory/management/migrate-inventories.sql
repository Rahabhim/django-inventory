
ALTER TABLE inventory_inventory ADD
    group_id INTEGER REFERENCES inventory_inventorygroup(id) ON DELETE CASCADE;

INSERT INTO inventory_inventorygroup(name, department_id, date_act, date_val, state,
        create_user_id, validate_user_id, signed_file)
    SELECT inv.name, common_location.department_id,
        inv.date_act, inv.date_val, inv.state,
        inv.create_user_id, inv.validate_user_id,
        inv.signed_file
    FROM inventory_inventory AS inv, common_location
        WHERE group_id IS NULL AND common_location.id = inv.location_id;

UPDATE inventory_inventory AS inv2 SET "group_id" = inv1.id
    FROM inventory_inventorygroup AS inv1,
        common_location 
    WHERE inv2.group_id IS NULL
      AND inv2.location_id = common_location.id
      AND (inv1.name, inv1.create_user_id, inv1.date_act, inv1.department_id) =
          (inv2.name, inv2.create_user_id, inv2.date_act, common_location.department_id)
      AND ( inv1.date_val = inv2.date_val OR ( inv1.date_val IS NULL AND inv2.date_val IS NULL))
      AND (inv1.signed_file = inv2.signed_file OR
            (inv1.signed_file IS NULL AND inv2.signed_file IS NULL));

UPDATE inventory_inventory SET signed_file = NULL WHERE "group_id" IS NOT NULL;

ALTER TABLE inventory_inventory DROP COLUMN signed_file ;

-- compare null?