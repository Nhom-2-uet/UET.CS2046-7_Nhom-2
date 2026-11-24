-- Run once against an existing chi_tieu_sinh_vien database.
ALTER TABLE budget_settings
    ADD COLUMN weekday_daily_limit_vnd BIGINT UNSIGNED NOT NULL DEFAULT 0
        AFTER monthly_budget_vnd,
    ADD COLUMN weekend_daily_limit_vnd BIGINT UNSIGNED NOT NULL DEFAULT 0
        AFTER weekday_daily_limit_vnd;
