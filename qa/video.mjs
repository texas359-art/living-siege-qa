import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
const output=path.resolve(process.env.BASTION_QA_OUTPUT||'bastion-qa-results');
const report=JSON.parse(fs.readFileSync(path.join(output,'report.json'),'utf8'));
assert.equal(report.result,'PASS');
const box=report.fightCanvas;
const width=Math.floor(box.width/2)*2,height=Math.floor(box.height/2)*2,x=Math.floor(box.x/2)*2,y=Math.ceil(box.y/2)*2;
const start=Math.max(0,report.duel.videoStartSeconds-.5),duration=Math.min(25,report.duel.videoEndSeconds-start+.3);
const args=['-hide_banner','-y','-i',path.join(output,report.video),'-ss',String(start),'-t',String(duration),'-vf',`crop=${width}:${height}:${x}:${y}`,'-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',path.join(output,'battle.mp4')];
const result=spawnSync('ffmpeg',args,{encoding:'utf8'});
fs.writeFileSync(path.join(output,'video-encode.log'),String(result.stdout??'')+String(result.stderr??'')+(result.error?.stack??''));
assert.ok(!result.error,`Cannot start ffmpeg: ${result.error?.message}; see video-encode.log`);
assert.equal(result.status,0,'ffmpeg failed: see video-encode.log');
report.battleVideo={file:'battle.mp4',source:report.video,trimStartSeconds:start,durationSeconds:duration,crop:{width,height,x,y},note:'Only scene cropping and timeline trimming; no speed-up, interpolation or replacement of the actual rendered gameplay.'};
const ab=report.animationCanvas,acrop=`crop=${Math.floor(ab.width/2)*2}:${Math.floor(ab.height/2)*2}:${Math.floor(ab.x/2)*2}:${Math.ceil(ab.y/2)*2}`;
const animation=spawnSync('ffmpeg',['-hide_banner','-y','-i',path.join(output,report.video),'-ss',String(report.animationVideoStart),'-t',String(report.animationVideoEnd-report.animationVideoStart),'-vf',acrop,'-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',path.join(output,'walk-attack.mp4')],{encoding:'utf8'});
fs.writeFileSync(path.join(output,'animation-encode.log'),String(animation.stdout??'')+String(animation.stderr??''));assert.equal(animation.status,0);
report.animationVideo={file:'walk-attack.mp4',start:report.animationVideoStart,end:report.animationVideoEnd};
fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2));

for(const [sequence,file] of [['animation','walk-attack.mp4'],['battle','battle.mp4']]){
 fs.renameSync(path.join(output,file),path.join(output,'live-'+file));
 const result=spawnSync('ffmpeg',['-hide_banner','-y','-framerate',String(report.frameCapture.fps),'-i',path.join(output,'frames-'+sequence,'%05d.png'),'-vf','pad=ceil(iw/2)*2:ceil(ih/2)*2','-an','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',path.join(output,file)],{encoding:'utf8'});
 fs.writeFileSync(path.join(output,sequence+'-frame-encode.log'),result.stderr??'');assert.equal(result.status,0);
}
report.liveBattleVideo=report.battleVideo;report.battleVideo={file:'battle.mp4',durationSeconds:20,fps:report.frameCapture.fps,method:report.frameCapture.method};
report.animationVideo={file:'walk-attack.mp4',durationSeconds:6.2,fps:report.frameCapture.fps,method:report.frameCapture.method};
fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2));
