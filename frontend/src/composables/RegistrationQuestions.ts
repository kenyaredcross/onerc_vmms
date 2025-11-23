import { ref } from "vue";

interface RegistrationResponse {
  question_id: string;
  question: string;
  response: string | string[];
}

export function registrationResponses() {
  const formResponse = ref<RegistrationResponse[]>([]);
  const responseKey = "registration_response";

  const loadResponses = () => {
    const responses = sessionStorage.getItem(responseKey);

    if (responses) {
      formResponse.value = JSON.parse(responses);
    }
  };

  loadResponses();

  const addResponses = (responses: RegistrationResponse[]) => {
    formResponse.value = responses;
    sessionStorage.setItem(responseKey, JSON.stringify(responses));
  };

  const clearResponses = () => {
    formResponse.value = [];
    sessionStorage.removeItem(responseKey);
  };

  return {
    formResponse,
    addResponses,
    clearResponses,
  };
}
