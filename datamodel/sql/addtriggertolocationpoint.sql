CREATE TRIGGER check_loc
  BEFORE INSERT OR UPDATE
  ON location_point
  FOR EACH ROW
  EXECUTE PROCEDURE check_location();
