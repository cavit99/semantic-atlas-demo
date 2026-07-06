export type Axis = {
  negativeLabel: string;
  positiveLabel: string;
  negativePrompt: string;
  positivePrompt: string;
};

export type DemoIdea = {
  id: string;
  title: string;
  family: string;
  scene: string;
  midpointPrompt: string;
  xAxis: Axis;
  yAxis: Axis;
  palette: string[];
  suffix: string;
};

export type GridCellEvent = {
  type: "cell";
  jobId: string;
  index: number;
  row: number;
  col: number;
  x: number;
  y: number;
  imageUrl: string;
  elapsedMs: number;
  backend: string;
};

export type GridDoneEvent = {
  type: "done";
  jobId: string;
  elapsedMs: number;
  backend: string;
};

export type GridProgressEvent = {
  type: "progress";
  jobId: string;
  phase: "rendering";
  completed: number;
  total: number;
  batchSize: number;
  indices: number[];
  elapsedMs: number;
  backend: string;
};

export type GridErrorEvent = {
  type: "error";
  jobId: string;
  message: string;
};

export type GridEvent = GridCellEvent | GridDoneEvent | GridProgressEvent | GridErrorEvent;
