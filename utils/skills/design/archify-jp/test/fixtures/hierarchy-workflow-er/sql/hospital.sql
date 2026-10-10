CREATE TABLE patients (id bigint PRIMARY KEY, name text NOT NULL, card_no text NOT NULL);
CREATE TABLE doctors (id bigint PRIMARY KEY, name text NOT NULL, dept text NOT NULL);
CREATE TABLE slots (id bigint PRIMARY KEY, doctor_id bigint NOT NULL REFERENCES doctors(id), starts_at timestamp NOT NULL, capacity integer NOT NULL);
CREATE TABLE appointments (id bigint PRIMARY KEY, slot_id bigint NOT NULL REFERENCES slots(id), patient_id bigint NOT NULL REFERENCES patients(id), status text NOT NULL);
SELECT s.id, s.capacity, d.dept FROM slots s INNER JOIN doctors d ON d.id = s.doctor_id WHERE s.starts_at = $1;
SELECT a.id FROM appointments a WHERE a.slot_id = $1 AND a.status = 'booked';
UPDATE appointments SET status = 'expired' WHERE slot_id = $1 AND status = 'held';
