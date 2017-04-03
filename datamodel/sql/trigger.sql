-- Function: check_location()

-- DROP FUNCTION check_location();

CREATE OR REPLACE FUNCTION check_location()
  RETURNS trigger AS
$BODY$
BEGIN
	IF unique_location(NEW.thegeometry) > 0 THEN
		INSERT into public.failed_location (thegeometry
		                                   ,locationdescription
		                                   ,orig_srid)
		VALUES (NEW.thegeometry
		       ,NEW.locationdescription
		       ,NEW.orig_srid);
		--RAISE EXCEPTION 'There is already a location on those coordinates...';
		RETURN NULL;
	END IF;	
	RETURN NEW;
END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;
ALTER FUNCTION check_location()
  OWNER TO postgres;
