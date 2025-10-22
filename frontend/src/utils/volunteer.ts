export interface VolunteerSignupData {
  mobile_money_number: string;
  date_of_birth: string;
  idpassport: string;
  marital_status: string;
  education: string;
  profession: string;
  place_of_work: string;
  reason_to_join: string;
  blood_group: string;
  allergies: string[];
  disabilities: string[];
  languages: string[];
  krcs_trainings: string[];
  additional_skills: string[];
}

export const initialVolunteerForm: VolunteerSignupData = {
  mobile_money_number: "",
  date_of_birth: "",
  idpassport: "",
  marital_status: "",
  education: "",
  profession: "",
  place_of_work: "",
  reason_to_join: "",
  blood_group: "",
  allergies: [],
  disabilities: [],
  languages: [],
  krcs_trainings: [],
  additional_skills: [],
};

export interface SignUp {
  first_name: string;
  last_name: string;
  email: string;
  gender: string;
  phone: string;
}

export const initialForm: SignUp = {
  first_name: "",
  last_name: "",
  email: "",
  gender: "",
  phone: "",
};

export function resetSignUpForm(form: SignUp) {
  form.first_name = "";
  form.last_name = "";
  form.email = "";
  form.gender = "";
  form.phone = "";
}

export function isValidPhone(phone: string) {
  const regex = /^\+254\d{9}$/;
  return regex.test(phone);
}
