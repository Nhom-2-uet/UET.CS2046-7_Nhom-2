-- Run against an existing chi_tieu_sinh_vien database after reviewing
-- the preflight queries below and correcting any rows they report.

USE chi_tieu_sinh_vien;

-- Preflight: these rows must be corrected before adding the composite FK.
SELECT t.transaction_id, t.category_id, t.transaction_type, c.type AS category_type
FROM transactions AS t
JOIN categories AS c ON c.category_id = t.category_id
WHERE t.transaction_type <> c.type;

-- Preflight: these rows must be resolved before adding the unique key.
SELECT paid_transaction_id, COUNT(*) AS linked_expense_count
FROM required_expenses
WHERE paid_transaction_id IS NOT NULL
GROUP BY paid_transaction_id
HAVING COUNT(*) > 1;

ALTER TABLE users
    MODIFY username VARCHAR(100) NULL,
    MODIFY password_hash VARCHAR(255) NULL;

ALTER TABLE categories
    ADD UNIQUE KEY uq_categories_id_type (category_id, type);

ALTER TABLE transactions
    DROP FOREIGN KEY fk_transactions_category,
    ADD CONSTRAINT fk_transactions_category_type
        FOREIGN KEY (category_id, transaction_type)
        REFERENCES categories(category_id, type)
        ON DELETE RESTRICT;

ALTER TABLE required_expenses
    ADD UNIQUE KEY uq_required_expenses_paid_transaction (paid_transaction_id);
