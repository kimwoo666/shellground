package org.shellground.learn;

import android.util.Base64;
import org.json.*;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Connects Android to the existing real guest grader; never runs host Conda.
 * All calls belong on the service worker. The injected interfaces allow isolated
 * protocol tests, which are not evidence of actual Linux/Conda execution.
 */
final class CondaGuest {
    interface Transport { Object request(String action,JSONObject payload,long timeout)throws Exception; }
    interface Assets { byte[] read(String name)throws Exception; }
    private final Transport transport;
    private final Assets assets;
    private JSONObject mission;
    private JSONObject setup;
    static final String WORKSPACE="/home/learner/conda-work";

    CondaGuest(Transport transport,Assets assets){this.transport=transport;this.assets=assets;}

    void configure()throws Exception{
        Map<String,byte[]> files=new LinkedHashMap<>();
        for(String name:new String[]{"conda_runtime.py","shell_snapshot.py","bashrc","pip_runtime.py","pip_wheel.py","conda_setup.py","installer_sources.py","guest_files.py"}){
            files.put("/opt/shellground/"+name,assets.read(name));
        }
        GuestAssets.sync(transport,files);
    }

    JSONObject prepare(JSONObject candidate)throws Exception{
        if(setup!=null)configure();
        setup=null;
        mission=null; // A failed prepare must never retain an older grading target.
        if(!"conda".equals(candidate.optString("kind")))throw new IOException("Conda 문제 형식이 아닙니다.");
        JSONObject problem=candidate.getJSONObject("problem");
        if(problem.getString("id").isEmpty())throw new IOException("Conda 문제 ID가 없습니다.");
        problem.getJSONArray("answer_fields");candidate.getJSONObject("probes");
        JSONObject actual=(JSONObject)transport.request("prepare",new JSONObject().put("mission",candidate),360000);
        if(!actual.optBoolean("ready")||!WORKSPACE.equals(actual.optString("start")))
            throw new IOException("Conda 실제 준비 결과를 확인하지 못했습니다.");
        JSONObject runtime=actual.getJSONObject("runtime");
        if(!runtime.optString("platform").startsWith("linux-")
            ||!"/opt/shellground/miniconda".equals(runtime.optString("root_prefix")))
            throw new IOException("실제 Linux guest의 Conda 정보가 일치하지 않습니다.");
        mission=new JSONObject(candidate.toString());
        return actual;
    }

    JSONObject grade(String session,JSONObject answers)throws Exception{
        if(setup!=null)return setupCall("grade",new JSONObject().put("prefix",setup.getString("prefix")));
        if(mission==null||session==null||session.isEmpty())throw new IOException("먼저 실제 Conda 문제를 준비하세요.");
        JSONObject submitted=typedAnswers(mission.getJSONObject("problem").getJSONArray("answer_fields"),answers);
        JSONObject actual=(JSONObject)transport.request("grade",new JSONObject().put("mission",mission)
            .put("session",session).put("answers",submitted),360000);
        actual.getBoolean("passed");actual.getJSONArray("checks");
        return actual; // Preserve failed checks. No local command-string grading.
    }

    JSONObject prepareSetup()throws Exception{
        mission=null;setup=null;
        exec(new JSONArray().put("/usr/bin/python3").put("-c")
            .put("from pathlib import Path;p=Path('/opt/shellground/bashrc');s=p.read_text();p.write_text(s.split('export CONDARC=')[0])"),true,"/tmp",null,5,10000);
        setup=setupCall("prepare",new JSONObject());return setup;
    }
    private JSONObject setupCall(String action,JSONObject payload)throws Exception{
        return new JSONObject(exec(new JSONArray().put("/opt/shellground/miniconda/bin/python").put("-I")
            .put("/opt/shellground/conda_setup.py").put(action),true,"/tmp",
            Base64.encodeToString(payload.toString().getBytes(StandardCharsets.UTF_8),Base64.NO_WRAP),120,150000));
    }

    static JSONObject typedAnswers(JSONArray fields,JSONObject submitted)throws Exception{
        Set<String> allowed=new HashSet<>();JSONObject result=new JSONObject();
        for(int i=0;i<fields.length();i++){
            JSONObject field=fields.getJSONObject(i);String key=field.getString("key");allowed.add(key);
            if(!submitted.has(key))continue; // Blank is unanswered, never implicit false.
            Object value=submitted.get(key);
            boolean bool=field.opt("expected") instanceof Boolean;
            if(bool?!(value instanceof Boolean):!(value instanceof String))
                throw new IOException("답안 입력 형식을 확인하세요: "+key);
            if(value instanceof String&&((String)value).length()>4096)throw new IOException("답안이 너무 깁니다.");
            result.put(key,value);
        }
        Iterator<String> keys=submitted.keys();
        while(keys.hasNext())if(!allowed.contains(keys.next()))throw new IOException("이 문제에 없는 답안 칸입니다.");
        return result;
    }

    JSONObject files(String relative)throws Exception{
        if(mission==null)throw new IOException("먼저 실제 Conda 문제를 준비하세요.");
        // This source was verified during configure; don't resend the full
        // reader over the serial channel every time the file tab is opened.
        JSONArray args=new JSONArray().put("/usr/bin/python3").put("/opt/shellground/guest_files.py")
            .put(relative==null?"list":"read");
        if(relative!=null)args.put(relative);
        return new JSONObject(exec(args,false,WORKSPACE,null,30,60000));
    }

    private String exec(JSONArray args,boolean root,String cwd,String input,int seconds,long timeout)throws Exception{
        JSONObject request=new JSONObject().put("argv",args).put("root",root).put("cwd",cwd).put("run_timeout",seconds);
        if(input!=null)request.put("input",input);
        JSONObject actual=(JSONObject)transport.request("exec",request,timeout);
        if(actual.getInt("code")!=0){
            String detail=new String(Base64.decode(actual.optString("err"),Base64.DEFAULT),StandardCharsets.UTF_8);
            throw new IOException(detail.length()>1000?detail.substring(detail.length()-1000):detail);
        }
        return new String(Base64.decode(actual.getString("out"),Base64.DEFAULT),StandardCharsets.UTF_8);
    }
}
