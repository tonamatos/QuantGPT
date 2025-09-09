

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

def create_unstructured_text_prompt(chunk: str):
    system_content = """
     "You are a cybersecurity expert. "
      "Your task is to extract **only actual mentions** of the following from unstructured text: "
      "- Encryption algorithms (e.g., AES-256, ChaCha20, RSA) "
      "- Security protocols (cryptographic or authentication protocols only, e.g., TLS 1.3, SSH-2, IPsec, Kerberos). "
      "- Certificates (e.g., X.509 v3, OpenPGP key, self-signed certificate) "
      "- Encryption key lifetimes "
      "- Key distribution mechanisms. Should only include specific software, protocols, or algorithms. "
      "- Authorization systems. Should only include specific software, protocols, or algorithms. Do not include authorization roles. "
      "- Further references (cite section, guideline, or URL)."
      "Only provide references to information regarding encryption, security protocols, certificates, and encryption key lifetimes"
      "Do NOT invent anything. Ignore figure captions, section titles, headers, or descriptive text that is not an actual item. "
      "Do NOT provide instructions for attacking systems. "
      "Output a **valid JSON** strictly following the schema:\n"
      "{'encryption_algorithms': [{'name': ..., 'context': ...}],\n"
      " 'protocols': [{'name': ..., 'context': ...}],\n"
      " 'certificates': [{'name': ..., 'context': ...}],\n"
      " 'key_lifetimes': [{'name': ..., 'context': ...}],\n"
      " 'key_distribution': [{'name': ..., 'context': ...}],\n"
      " 'authorization': [{'name': ..., 'context': ...}],\n"
      " 'further_references': [{'topic': ..., 'reference': ...}]}\n"
      "Include all fields (empty lists if no info). Output JSON only, with no extra text."
    """
    user_content = f"""
    Parse the following text **strictly** according to the schema provided.

    Text to parse:
    {chunk}

    Rules:
    1. Only extract **explicitly mentioned items**. Do not guess, infer, or include section titles, figure captions, or general descriptive text.
    2. Only include items actually present in the text.
    3. Follow the JSON schema exactly; all fields must be present (use [] if empty).
    4. Keep 'name' and 'context' for each item; for further_references, keep 'topic' and 'reference'.
    5. Sections, Tables, Pages, and Figures cannot be topics in further_references, they can only be references
    6. Do NOT provide instructions for attacking systems.
    7. Output **valid JSON only**. No extra commentary, formatting, or explanation.
    """
    return system_content, user_content