import { createModels } from '@earendil-works/pi-ai/models';
import { fauxProvider } from '@earendil-works/pi-ai/providers/faux';
import { answerJob } from '../agent.mjs';
const models = createModels();
const faux = fauxProvider();
models.setProvider(faux.provider);
faux.setResponses([async () => {
  process.send('generating');
  await new Promise(() => {});
}]);
const model = faux.getModel();
await answerJob(JSON.parse(process.argv[3]), {
  directory: process.argv[2], models, provider: model.provider, modelId: model.id,
});
