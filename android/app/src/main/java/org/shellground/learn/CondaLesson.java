package org.shellground.learn;

import org.json.*;

/** Learner-facing text only. Never render the private mission or answer values. */
final class CondaLesson {
    static String lines(JSONArray values){
        StringBuilder text=new StringBuilder();
        if(values!=null)for(int i=0;i<values.length();i++){if(i>0)text.append('\n');text.append(values.optString(i));}
        return text.toString();
    }
    static String step(JSONObject page){
        return page.optString("explanation")+"\n\n직접 해볼 예시\n"+lines(page.optJSONArray("commands"))
            +"\n\n확인할 내용\n"+page.optString("observe");
    }
    static String problem(JSONObject problem,boolean example)throws JSONException{
        JSONObject fixture=problem.getJSONObject("initial_fixture");
        StringBuilder text=new StringBuilder("시작 위치: "+CondaGuest.WORKSPACE+"\n\n준비된 환경\n");
        JSONArray envs=fixture.getJSONArray("environments");
        if(envs.length()==0)text.append("학습 환경 없음 (관리용 base는 별도)\n");
        for(int i=0;i<envs.length();i++)text.append("• ").append(envs.getJSONObject(i).getString("name")).append('\n');
        text.append("현재 활성: ").append(fixture.isNull("active_env")?"없음":fixture.optString("active_env","없음"));
        JSONArray files=fixture.optJSONArray("files");
        if(files!=null&&files.length()>0){
            text.append("\n준비된 파일·폴더:");
            for(int i=0;i<files.length();i++)text.append('\n').append(files.getJSONObject(i).getString("path"));
        }
        text.append("\n\n목표\n").append(problem.getString("goal"));
        if(example){
            JSONArray commands=problem.optJSONArray("example_commands");
            text.append("\n\n따라 입력할 예시\n").append(lines(commands));
            boolean transaction=false;
            if(commands!=null)for(int i=0;i<commands.length();i++)
                if(commands.optString(i).matches("conda (create|install|update|remove|env create|env remove) .*"))transaction=true;
            if(transaction)text.append("\n\n설치·제거 계획의 대상이 맞는지 읽고 확인 질문에 직접 응답하세요.");
        }
        else if(problem.getJSONArray("provided_diagnostics").length()>0)
            text.append("\n\n제공 진단식\n").append(lines(problem.getJSONArray("provided_diagnostics")))
                .append("\n\n").append(problem.getString("diagnostic_notice"));
        return text.toString();
    }
    static String bootstrap(JSONObject data)throws JSONException{
        JSONObject entry=data.getJSONObject("bootstrap");StringBuilder text=new StringBuilder(entry.getString("explanation"));
        JSONArray concepts=entry.getJSONArray("concepts");
        for(int i=0;i<concepts.length();i++)text.append("\n\n").append(concepts.getJSONObject(i).getString("text"));
        text.append("\n\n준비 실패 시\n").append(entry.getJSONObject("readiness_gate").getString("on_failure"));
        JSONObject install=entry.getJSONObject("optional_install_exercise");
        text.append("\n\n메뉴 → Miniconda 설치 실습\n").append(install.getString("goal"))
            .append("\n\n").append(install.getString("explanation"))
            .append("\n\n").append(lines(install.getJSONArray("microsteps")))
            .append("\n\n설치 실습을 열면 이번 실습의 경로와 라이선스가 표시됩니다. 안내를 읽은 것만으로 완료 처리하지 않습니다.");
        return text.toString();
    }
}
