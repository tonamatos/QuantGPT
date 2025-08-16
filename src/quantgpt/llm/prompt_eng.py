

def create_threat_modeling_prompt(components_data):
  prompt = '''You are a quantum cryptography researcher expert in cybersecurity and the STRIDE framework.
              Your task is to analyze the provided system components descriptions and identify potential
              post-quantum security threats. Give your answer in a JSON format with the following structure:

              {component_name: ,
                threats: [
                    {threat_type: ,
                     threat_description: ,
                     threat_impact: ,
                     possible_mitigation: ,}
                ]
              }

              The STRIDE threat types are: Spoofing, Tampering, Repudiation, Information Disclosure,
              Denial of Service, Elevation of Privilege. You may use others if you find them relevant.

              Give special attention to threats that could be exacerbated by the advent of quantum computing.

              Here are the system components descriptions:
              ''' + str(components_data)

  return prompt