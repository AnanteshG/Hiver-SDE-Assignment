# Human annotation guide — version 1 (provisional until development review)

## Unit and scope

Read the incoming customer message and displayed prior context. Do not inspect the
future brand response or model prediction while labelling. We evaluate the NEXT
public response, not successful resolution. English eligibility must be checked
manually; exclude non-English messages with a note. Exclusions reduce the scored
sample; document them and sample replacements within the same partition if needed.

## Intent definitions

| Intent | Definition | Boundary |
|---|---|---|
| account_access | Apple ID, passwords, sign-in, locked accounts | A cloud storage capacity issue is app_service |
| billing_purchase | Charges, subscriptions, refunds, purchases | Battery charging is battery_power |
| battery_power | Battery drain, charging, overheating, power | Physical broken charging port may be hardware_repair |
| connectivity | Wi-Fi, Bluetooth, cellular, network connections | Signing into an account is account_access |
| software_update | Installation, OS updates, general software bugs | An update mentioned only as timing does not override the specific symptom |
| hardware_repair | Damage, repairs, broken components, warranty | Unclear software-versus-hardware faults may need a note |
| app_service | App-specific behaviour, music, cloud, photos, storage | Use a more specific billing/account/network intent when that is the request |
| other_unclear | Insufficient context or unsupported issue | Do not infer an issue from a missing image or link |

For multiple issues choose the customer's main requested action. If no main issue
is identifiable, choose other_unclear and explain. These definitions were drafted
from an initial data inspection; refine them using only the 50 development cases,
then record the frozen version before labelling the test set.

## Human required

Choose Yes when account access, a refund, repair eligibility, private information,
physical safety, inadequate context, or unsupported advice requires a specialist.
Choose No only when a safe, useful next public response is possible without those
capabilities. A targeted clarification may qualify; a vague acknowledgement does
not demonstrate resolution. Judge the request, not whether a historical agent
chose to move it to DM. Missing images/links can make the message ambiguous.

Record the handling reason, what an acceptable response must accomplish, and
claims/requests to avoid. Write "No additional constraints beyond the general
policy" when appropriate rather than leaving the field blank.

## Process

1. Label 20 development examples, identify ambiguous boundaries, revise this guide.
2. Complete 50 development labels and freeze the guide and handling policy.
3. Label 120 representative and 30 challenge examples without model outputs.
4. Have another human independently label 30 if possible; otherwise re-label a
   subset later and report intra-annotator consistency, not inter-annotator agreement.
5. Freeze the annotated file hash before final inference. Do not tune on test errors.

The application requires a reviewer ID and personal-review confirmation. These are
provenance records, not a technical guarantee that the review occurred. Do not
claim AI-generated labels as human labels.

## Optional development hints

The dashboard offers explicitly AI-authored suggestions for the 50 development
examples. They are separate from the golden data and never populate or save labels.
Development outputs had already been inspected when preparing these hints; they are
not blinded annotations. Decide your own labels and disclose this assistance in the
sampling note if used. Representative/challenge examples and human reply ratings
remain independent. No suggestion counts towards the human annotation requirement.
