-- PostgreSQL equivalents of the business rules in sql/02_triggers_procedures.sql.
-- No reset is performed. Execute explicitly as the schema owner.
CREATE OR REPLACE FUNCTION public.pharmacy_prepare_sale_item()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
    available integer;
    expires_on date;
    batch_price numeric(12,2);
BEGIN
    -- Locks the batch until the surrounding checkout transaction commits or rolls back.
    -- Concurrent checkouts re-check the latest row version after waiting on this lock.
    SELECT b.quantityleft, b.expirydate, b.unitprice
      INTO available, expires_on, batch_price
      FROM public.inventory_batches AS b
     WHERE b.batchid = NEW.batchid
     FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Sale blocked: batch was not found' USING ERRCODE = '23503';
    ELSIF expires_on <= CURRENT_DATE THEN
        RAISE EXCEPTION 'Sale blocked: batch is expired' USING ERRCODE = '23514';
    ELSIF available < NEW.quantitysold THEN
        RAISE EXCEPTION 'Sale blocked: insufficient stock in batch' USING ERRCODE = '23514';
    END IF;

    NEW.subtotal := NEW.quantitysold * batch_price;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.pharmacy_apply_sale_item()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
BEGIN
    -- The BEFORE trigger has locked this row for this transaction.
    UPDATE public.inventory_batches
       SET quantityleft = quantityleft - NEW.quantitysold
     WHERE batchid = NEW.batchid;

    UPDATE public.transactions
       SET totalamount = totalamount + NEW.subtotal
     WHERE transactionid = NEW.transactionid;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_sale_before_insert ON public.sales_items;
CREATE TRIGGER trg_sale_before_insert
BEFORE INSERT ON public.sales_items
FOR EACH ROW EXECUTE FUNCTION public.pharmacy_prepare_sale_item();

DROP TRIGGER IF EXISTS trg_sale_after_insert ON public.sales_items;
CREATE TRIGGER trg_sale_after_insert
AFTER INSERT ON public.sales_items
FOR EACH ROW EXECUTE FUNCTION public.pharmacy_apply_sale_item();

-- PostgreSQL set-returning replacement for MySQL sp_fifo_batches(p_drug_id).
CREATE OR REPLACE FUNCTION public.sp_fifo_batches(p_drug_id integer)
RETURNS TABLE(batchid integer, batchnumber varchar, quantityleft integer, expirydate date, unitprice numeric)
LANGUAGE sql
STABLE
AS $$
    SELECT b.batchid, b.batchnumber, b.quantityleft, b.expirydate, b.unitprice
      FROM public.inventory_batches AS b
     WHERE b.drugid = p_drug_id
       AND b.quantityleft > 0
       AND b.expirydate > CURRENT_DATE
     ORDER BY b.expirydate, b.batchid;
$$;

REVOKE ALL ON FUNCTION public.pharmacy_prepare_sale_item() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.pharmacy_apply_sale_item() FROM PUBLIC;
