package org.shellground.learn;

import android.util.Base64;
import org.json.*;
import java.io.IOException;
import java.nio.charset.StandardCharsets;

/** Android transport for the same real Jupyter service used by desktop. */
final class NotebookGuest {
    private final CondaGuest.Transport transport;
    private JSONObject baseline,problem;
    private static final String SERVICE="/opt/shellground/notebook-assets/guest_service.py";
    NotebookGuest(CondaGuest.Transport transport){this.transport=transport;}
    static String decode(JSONObject result,String key){return new String(Base64.decode(result.optString(key),Base64.DEFAULT),StandardCharsets.UTF_8);}
    void start()throws Exception{
        try{startService();}catch(Exception error){
            String detail="";
            try{
                JSONObject log=(JSONObject)transport.request("exec",new JSONObject().put("root",true).put("cwd","/tmp").put("run_timeout",15)
                    .put("argv",new JSONArray().put("/usr/bin/python3").put("-c")
                        .put("from pathlib import Path;p=Path('/opt/shellground/notebook/service.log');print(p.read_text()[-6000:] if p.exists() else 'No service log')")),25000);
                detail=decode(log,"out");
            }catch(Exception diagnostic){detail=diagnostic.toString();}
            throw new IOException("Jupyter 시작 준비: "+error.getMessage()+"\n"+detail,error);
        }
    }
    private void startService()throws Exception{
        // This adapter is constructed once immediately after a fresh VM boot.
        // A PID receipt left in an immutable base cannot own a process in this
        // new boot. Remove only that stale receipt, never a process by old PID.
        JSONObject cleared=(JSONObject)transport.request("exec",new JSONObject().put("root",true).put("cwd","/tmp")
            .put("argv",new JSONArray().put("/usr/bin/python3").put("-c")
                .put("from pathlib import Path;Path('/opt/shellground/notebook/service.json').unlink(missing_ok=True)")),15000);
        if(cleared.getInt("code")!=0)throw new IOException(decode(cleared,"err"));
        JSONObject result=(JSONObject)transport.request("exec",new JSONObject().put("root",true).put("cwd","/tmp")
            .put("run_timeout",120).put("argv",new JSONArray().put("/usr/bin/python3").put("/opt/shellground/notebook-assets/guest_setup.py")),125000);
        if(result.getInt("code")!=0)throw new IOException(decode(result,"err"));
        long deadline=android.os.SystemClock.elapsedRealtime()+90000;
        while(true){try{call("ping",new JSONObject());break;}catch(Exception error){if(android.os.SystemClock.elapsedRealtime()>deadline)throw error;Thread.sleep(200);}}
        String script="from pathlib import Path;p=Path('/opt/shellground/bashrc');p.write_text(p.read_text()+"+
            "'\\nsource /opt/shellground/miniconda/etc/profile.d/conda.sh\\nexport CONDARC=/opt/shellground/condarc CONDA_OFFLINE=true CONDA_NO_PLUGINS=true CONDA_SOLVER=classic\\n"+
            "export JUPYTER_DATA_DIR=/home/learner/notebook-jupyter/share/jupyter PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1\\n"+
            "conda activate /home/learner/notebook-envs/data\\n')";
        result=(JSONObject)transport.request("exec",new JSONObject().put("root",true).put("cwd","/tmp")
            .put("argv",new JSONArray().put("/usr/bin/python3").put("-c").put(script)),20000);
        if(result.getInt("code")!=0)throw new IOException(decode(result,"err"));
    }
    JSONObject call(String action,JSONObject arguments)throws Exception{
        JSONObject payload=new JSONObject(arguments.toString()).put("action",action);
        // Don't import the full Jupyter controller for every tiny socket poll.
        // Only the persistent guest service needs the controller dependencies.
        String client="import sys,socket; s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);s.settimeout(12);s.connect('/home/learner/.shellground-notebook.sock');s.sendall(sys.stdin.buffer.read().rstrip(b'\\n')+b'\\n');f=s.makefile('rb');r=f.readline(3145729);assert len(r)<=3145728;sys.stdout.buffer.write(r);f.close();s.close()";
        JSONObject response=(JSONObject)transport.request("exec",new JSONObject().put("root",false)
            .put("cwd","/home/learner/notebook-work").put("run_timeout",30)
            .put("argv",new JSONArray().put("/usr/bin/python3").put("-c").put(client))
            .put("input",Base64.encodeToString(payload.toString().getBytes(StandardCharsets.UTF_8),Base64.NO_WRAP)),40000);
        if(response.getInt("code")!=0)throw new IOException(decode(response,"err"));
        JSONObject value=new JSONObject(decode(response,"out"));
        if(!value.optBoolean("ok"))throw new IOException(value.optString("error","Jupyter 응답 오류"));
        return value.getJSONObject("value");
    }
    JSONObject perform(String operation,JSONObject arguments)throws Exception{
        if(operation.equals("run_all")){
            JSONArray batch=new JSONArray(),cells=arguments.getJSONArray("cells");
            int used=0;
            if(cells.length()>32)throw new IOException("셀 개수 제한을 초과했습니다.");
            for(int i=0;i<cells.length();i++){
                JSONObject cell=cells.getJSONObject(i);if(!cell.getString("type").equals("code"))continue;
                JSONObject result=perform("execute",new JSONObject().put("cell_id",cell.getString("id")).put("code",cell.getString("source")));
                if(used+result.toString().getBytes(StandardCharsets.UTF_8).length>350000){result.put("messages",new JSONArray());result.put("truncated",true);}
                used+=result.toString().getBytes(StandardCharsets.UTF_8).length;
                batch.put(new JSONObject().put("cell_id",cell.getString("id")).put("result",result));
                if(!result.optBoolean("ok"))break;
            }
            return new JSONObject().put("batch",batch);
        }
        JSONObject request=new JSONObject(arguments.toString()).put("operation",operation);
        String job=call("begin",new JSONObject().put("request",request)).getString("job");
        // Setup/grade can inspect two environments and cold-start a real
        // kernel on a software-emulated ARM guest. UI stop remains immediate;
        // this bound is not a main-thread wait or an unbounded retry loop.
        long deadline=android.os.SystemClock.elapsedRealtime()+900000;
        while(!Thread.currentThread().isInterrupted()){
            JSONObject response=call("poll",new JSONObject().put("job",job));
            if(response.optBoolean("done")){
                JSONObject result=response.getJSONObject("result");
                if(operation.equals("execute")){
                    result.put("cell_id",arguments.getString("cell_id"));
                    if(result.toString().length()>64000){
                        String preview=result.toString().substring(0,4000);
                        result.put("messages",new JSONArray().put(new JSONObject().put("type","stream")
                            .put("content",new JSONObject().put("text",preview+"\n… 화면 표시 한도 초과"))));
                        result.put("truncated",true);
                    }
                }
                return result;
            }
            if(android.os.SystemClock.elapsedRealtime()>deadline){interrupt();throw new IOException("Jupyter 작업 시간이 초과되었습니다. 입력 코드는 유지됩니다.");}
        }
        throw new InterruptedException("노트북 작업 취소");
    }
    JSONObject prepare(JSONObject candidate)throws Exception{
        baseline=null;problem=null;
        JSONObject value=perform("prepare",new JSONObject().put("problem",candidate));
        baseline=value;problem=new JSONObject(candidate.toString());
        return new JSONObject().put("start","/home/learner/notebook-work").put("notebook",value)
            .put("kernels",perform("list",new JSONObject()).getJSONArray("kernels"));
    }
    JSONObject grade(JSONArray cells)throws Exception{
        if(baseline==null)throw new IOException("먼저 노트북 문제를 준비하세요.");
        return perform("grade",new JSONObject().put("problem",problem).put("baseline",baseline).put("cells",cells));
    }
    void interrupt()throws Exception{call("interrupt",new JSONObject());}
}
