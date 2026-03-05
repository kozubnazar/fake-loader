SET FOREIGN_KEY_CHECKS=0;

DROP TABLE IF EXISTS receiptitem;
DROP TABLE IF EXISTS receipt;
DROP TABLE IF EXISTS terminal;
DROP TABLE IF EXISTS store;
DROP TABLE IF EXISTS storegroup;
DROP TABLE IF EXISTS product;
DROP TABLE IF EXISTS brand;
DROP TABLE IF EXISTS category;

SET FOREIGN_KEY_CHECKS=1;

CREATE TABLE category (
    id VARCHAR(100) NOT NULL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    parent_id VARCHAR(100) NULL,
    INDEX idx_category_parent (parent_id),
    CONSTRAINT fk_category_parent FOREIGN KEY (parent_id) REFERENCES category(id)
) ENGINE=InnoDB;

CREATE TABLE brand (
    id VARCHAR(100) NOT NULL PRIMARY KEY,
    name VARCHAR(200) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE storegroup (
    id VARCHAR(100) NOT NULL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    parent_id VARCHAR(100) NULL,
    INDEX idx_storegroup_parent (parent_id),
    CONSTRAINT fk_storegroup_parent FOREIGN KEY (parent_id) REFERENCES storegroup(id)
) ENGINE=InnoDB;

CREATE TABLE store (
    id VARCHAR(100) NOT NULL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    group_id VARCHAR(100) NULL,
    trade_area DECIMAL(20,4) NULL,
    place VARCHAR(200) NULL,
    address VARCHAR(200) NULL,
    INDEX idx_store_group (group_id),
    CONSTRAINT fk_store_group FOREIGN KEY (group_id) REFERENCES storegroup(id)
) ENGINE=InnoDB;

CREATE TABLE terminal (
    id VARCHAR(100) NOT NULL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    store_id VARCHAR(100) NOT NULL,
    INDEX idx_terminal_store (store_id),
    CONSTRAINT fk_terminal_store FOREIGN KEY (store_id) REFERENCES store(id)
) ENGINE=InnoDB;

CREATE TABLE product (
    id VARCHAR(100) NOT NULL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    code VARCHAR(100) NOT NULL,
    barcode TEXT NULL,
    category_id VARCHAR(100) NOT NULL,
    INDEX idx_product_category (category_id),
    CONSTRAINT fk_product_category FOREIGN KEY (category_id) REFERENCES category(id)
) ENGINE=InnoDB;

CREATE TABLE receipt (
    id VARCHAR(100) NOT NULL PRIMARY KEY,
    store_id VARCHAR(100) NOT NULL,
    terminal_id VARCHAR(100) NOT NULL,
    opened_at DATETIME NOT NULL,
    closed_at DATETIME NOT NULL,
    INDEX idx_receipt_store (store_id),
    INDEX idx_receipt_terminal (terminal_id),
    INDEX idx_receipt_closed (closed_at),
    CONSTRAINT fk_receipt_store FOREIGN KEY (store_id) REFERENCES store(id),
    CONSTRAINT fk_receipt_terminal FOREIGN KEY (terminal_id) REFERENCES terminal(id)
) ENGINE=InnoDB;

CREATE TABLE receiptitem (
    id VARCHAR(100) NOT NULL PRIMARY KEY,
    receipt_id VARCHAR(100) NOT NULL,
    product_id VARCHAR(100) NOT NULL,
    receipt_closed_at DATETIME NOT NULL,
    price DECIMAL(20,4) NOT NULL,
    qty DECIMAL(20,4) NOT NULL,
    turnover DECIMAL(20,4) NOT NULL,
    cost_price DECIMAL(20,4) NOT NULL,
    INDEX idx_receiptitem_receipt (receipt_id),
    INDEX idx_receiptitem_product (product_id),
    INDEX idx_receiptitem_closed (receipt_closed_at),
    CONSTRAINT fk_receiptitem_receipt FOREIGN KEY (receipt_id) REFERENCES receipt(id),
    CONSTRAINT fk_receiptitem_product FOREIGN KEY (product_id) REFERENCES product(id)
) ENGINE=InnoDB;
