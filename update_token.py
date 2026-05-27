#!/usr/bin/env python
import os

file_path = os.path.join(os.path.dirname(__file__), 'app.py')

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace old token components with new ones
replacements = [
    ('"id":43135,', '"id":43111,'),
    ('e571f971-6a50-4516-9ac5-b3136764', '807cbd83-b101-4893-b20a-09ac474f4728'),
    ('"iat":1774438229,', '"iat":1776070760,'),
    ('"jti":"44aa572b-0e33-4b7c-b9b3-7cf51a46ea61"', '"jti":"d2ac66ed-94e2-4f9e-a5a7-eb8a9aa40c50"'),
    ('W3IOhSR0Ke_inV_xUI8Xgy7lkPJliT_dKuaSw8HePlpVzLaud5HZA38A9gOUK06OBsdtQRu7qsrvLW5-FtI0MGMsiUYcWvhNhW9q8IRuZebct6qsjC0CKLAvPVbnRFOk9aM8f4HXmNHmRA6BI-u-c4pJrHuMSfbN1nHhFbliaL8GyNVfYspi7G8h0jM6Kfi5AKhzuguQHWS7HGm8Gge9BHyG9bi5azV0NcUYJmNl_So0-2lfsuqgys91Q9j6ZaaCBNyODZMSL5Mi2RIyGfZRRqQ9DiDGh5CVF_NyVlpgQHwUwkmC5O4IvSF88MoiFiVU1H3CxZDv9Gyw5QWe-vH33w==', 'LWezBMtwJDUZrsiAndP5Jy2uLyCsXEZrLN4PdNUOofKazVBcBA3g-udCG98I-S-fkkcMRBliwDf9dLruYLTdr07GMie6VNFbrE9ysGNznRYrEjAILU-rTir5gjnbWnXb5AtDD_3MskBDjKE7M2HXx9g2JRJSMB2vC60QzB8VqJp60415xFlWM0cjlwPOxQMu8QBw70pIdgfTdc6wO9hjVwaCvtTlLoaav4xdmJ9kHPOuwXXric7_2XpAwhs4VQzFsw1gJqgIn1WIQU49xMbu_xl-ejgxXtpHEyj0omxpftyW4sKrlHD_eOE_I4M5tyrQgaUPaTvHBLZPOfvgi0Eo_w=='),
]

for old, new in replacements:
    if old in content:
        content = content.replace(old, new)
        print(f'[OK] Replaced: {old[:50]}...')
    else:
        print(f'[NOT FOUND] {old[:50]}...')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('\nToken update complete!')
