var articles = [];

GREEN = "#7dcea0";
RED = "#f1948a";
BLUE = "#bb8fce";
GREY = "#e0e0e0";

$("document").ready(function() {
    textfield_left = document.getElementById("textfield_left");
    textfield_right = document.getElementById("textfield_right");
    article_select = document.getElementById("article");
    file_select = document.getElementById("evaluation_file");

    parse_benchmark();
    
    get_runs("evaluation-results");
});

function parse_benchmark() {
    $.get("development_labels.jsonl",
        function(data, status) {
            lines = data.split("\n");
            for (line of lines) {
                if (line.length > 0) {
                    json = JSON.parse(line);
                    labelled_text = json.text;
                    for (label of json.labels.reverse()) {
                        span = label[0];
                        begin = span[0];
                        end = span[1];
                        entity_id = label[1];
                        wikidata_url = "https://www.wikidata.org/wiki/" + entity_id;
                        before = labelled_text.substring(0, begin);
                        after = labelled_text.substring(end);
                        entity_text = labelled_text.substring(begin, end);
                        entity_representation = entity_text + " [" + entity_id + "]";
                        link = "<a href=\"" + wikidata_url + "\">" + entity_representation +"</a>";
                        labelled_text = before + link + after;
                    }
                    labelled_text = labelled_text.replaceAll("\n", "<br>");
                    json.labelled_text = labelled_text;
                    articles.push(json);
                }
            }
            set_article_select_options();
        }
    );
}

function set_article_select_options() {
    for (ai in articles) {
        article = articles[ai];
        var option = document.createElement("option");
        option.text = article.title;
        option.value = ai;
        article_select.add(option);
    }
    $("#article").prop("selectedIndex", -1);
}

function show_article_link() {
    $("#article_link").html("<a href=\"" + article.url + "\" target=\"_blank\">Wikipedia article</a>");
}

function show_ground_truth_entities() {
    annotations = [];
    for (eval_case of evaluation_cases[index]) {
        if ("true_entity" in eval_case) {
            if ("predicted_entity" in eval_case) {
                if (eval_case.predicted_entity.entity_id == eval_case.true_entity.entity_id) {
                    color = GREEN;
                } else {
                    color = RED;
                }
            } else {
                color = BLUE;
            }
            /*link = "<a href=\"" + wikidata_url + "\" style=\"background-color:" + color + "\" target=\"_blank\">" + text + "</a>";
            tooltip = "<div class=\"tooltip\">";
            tooltip += link;
            tooltip += "<span class=\"tooltiptext\">";
            tooltip += eval_case.true_entity.name + " (" + eval_case.true_entity.entity_id + ")";
            tooltip += "</span>";
            tooltip += "</div>";*/
            var annotation = {
                "span": eval_case.span,
                "color": color,
                "entity_name": eval_case.true_entity.name,
                "entity_id": eval_case.true_entity.entity_id
            };
            annotations.push(annotation);
        }
    }
    
    ground_truth_text = annotate_text(article.text, annotations);
    textfield_left.innerHTML = ground_truth_text;
}

function show_linked_entities() {
    article_cases = evaluation_cases[index];
    article_data = articles_data[index];
    
    evaluation_begin = article_data.evaluation_span[0];
    evaluation_end = article_data.evaluation_span[1];
    
    mentions = [];
    
    for (prediction of article_data.entity_mentions) {
        if (prediction.span[1] < evaluation_begin) {
            mentions.push(prediction);
        }
    }
    for (eval_case of article_cases) {
        mentions.push(eval_case);
    }
    for (prediction of article_data.entity_mentions) {
        if (prediction.span[0] >= evaluation_end) {
            mentions.push(prediction);
        }
    }
    
    annotations = []
    
    for (eval_case of mentions) {
        if ("linked_by" in eval_case || "predicted_entity" in eval_case) {
            if ("true_entity" in eval_case || "predicted_entity" in eval_case) {
                if ("true_entity" in eval_case) {
                    if (eval_case.true_entity.entity_id == eval_case.predicted_entity.entity_id) {
                        color = GREEN;
                    } else {
                        color = RED;
                    }
                } else {
                    color = BLUE;
                }
                entity_id = eval_case.predicted_entity.entity_id;
                entity_name = eval_case.predicted_entity.name;
                predicted_by = eval_case.predicted_by;
            } else {
                color = GREY;
                entity_id = eval_case.id;
                entity_name = null;
                predicted_by = eval_case.linked_by;
            }
            var annotation = {
                "span": eval_case.span,
                "color": color,
                "entity_name": entity_name,
                "predicted_by": predicted_by,
                "entity_id": entity_id
            };
            annotations.push(annotation);
        }
    }
    
    predicted_text = annotate_text(article.text, annotations);
    
    textfield_right.innerHTML = predicted_text;
}

function annotate_text(text, annotations) {
    for (annotation of annotations.reverse()) {
        before = text.substring(0, annotation.span[0]);
        snippet = text.substring(annotation.span[0], annotation.span[1]);
        after = text.substring(annotation.span[1]);
        wikidata_url = "https://www.wikidata.org/wiki/" + annotation.entity_id;
        entity_link = "<a href=\"" + wikidata_url + "\" target=\"_blank\">" + annotation.entity_id + "</a>";
        if (annotation.entity_name != null) {
            tooltip_text = annotation.entity_name + " (" + entity_link + ")";
        } else {
            tooltip_text = entity_link;
        }
        replacement = "<div class=\"tooltip\" style=\"background-color:" + annotation.color + "\">";
        replacement += snippet;
        replacement += "<span class=\"tooltiptext\">" + tooltip_text + "</span>";
        replacement += "</div>";
        text = before + replacement + after;
    }
    annotations.reverse();
    text = text.replaceAll("\n", "<br>");
    return text;
}

function show_table() {
    table = "<table class=\"casesTable\">\n";
    
    table += "<tr>";
    table += "<th>span</th>";
    table += "<th>text</th>";
    table += "<th>true ID</th>";
    table += "<th>true name</th>";
    table += "<th>detected</th>";
    table += "<th>predicted ID</th>";
    table += "<th>predicted name</th>";
    table += "<th>case</th>";
    table += "</tr>";
    
    for (eval_case of evaluation_cases[index]) {
        if ("true_entity" in eval_case) {
            has_true_entity = true;
            true_entity_id = eval_case.true_entity.entity_id;
            true_entity_name = eval_case.true_entity.name;
        } else {
            has_true_entity = false;
            true_entity_id = "-";
            true_entity_name = "-";
        }
        
        if (has_true_entity) {
            if (eval_case.detected) {
                detected = "true positive";
            } else {
                detected = "false negative";
            }
        } else {
            detected = "false positive";
        }
        
        if ("predicted_entity" in eval_case) {
            has_prediction_entity = true;
            predicted_entity_id = eval_case.predicted_entity.entity_id;
            predicted_entity_name = eval_case.predicted_entity.name;
        } else {
            has_prediction_entity = false;
            predicted_entity_id = "-";
            predicted_entity_name = "-";
        }
        
        if (has_prediction_entity && has_true_entity) {
            if (predicted_entity_id == true_entity_id) {
                case_type = "true positive";
            } else {
                case_type = "wrong entity";
            }
        } else if (has_prediction_entity) {
            case_type = "false positive";
        } else {
            case_type = "false negative";
        }
    
        table += "<tr>";
        table += "<td>" + eval_case.span[0] + ", " + eval_case.span[1] + "</td>";
        table += "<td>" + article.text.substring(eval_case.span[0], eval_case.span[1]) + "</td>";
        table += "<td>" + true_entity_id + "</td>";
        table += "<td>" + true_entity_name + "</td>";
        table += "<td>" + detected + "</td>";
        table += "<td>" + predicted_entity_id + "</td>";
        table += "<td>" + predicted_entity_name + "</td>";
        table += "<td>" + case_type + "</td>";
        table += "</tr>\n";
    }
    table += "</table>";
    $("#table").html(table);
}

function show_article() {
    index = article_select.value;
    
    if (index == "") {
        return;
    }
    article = articles[index];
    
    show_article_link();
    
    if (evaluation_cases.length == 0) {
        textfield_left.innerHTML = article.labelled_text;
        textfield_right.innerHTML = "ERROR: no file with cases found.";
        $("#table").html("");
        return;
    }
    
    show_ground_truth_entities();
    show_linked_entities();
    show_table();
}

function get_runs(path) {
    console.log(path);
    folders = [];
    
    promise = new Promise(function(request_done) {
        $.get(path, function(data) {
            request_done(data);
        });    
    });
    
    promise.then(function(data) {
        $(data).find("a").each(function() {
            name = $(this).attr("href");
            name = name.substring(0, name.length - 1);
            folders.push(name);
        });
        get_cases_files(path, folders);
    });
}

function get_cases_files(path, folders) {
    result_files = {};
    folders.forEach(function(folder) {
        $.get(path + "/" + folder, function(folder_data) {
            console.log(path + "/" + folder);
            $(folder_data).find("a").each(function() {
                file_name = $(this).attr("href");
                if (file_name.endsWith(".cases")) {
                    approach_name = file_name.substring(0, file_name.length - 6);
                    result_files[approach_name] = path + "/" + folder + "/" + approach_name;
                    
                    option = document.createElement("option");
                    option.text = approach_name;
                    option.value = approach_name;
                    file_select.add(option);
                    
                    $("#evaluation_file").prop("selectedIndex", -1);
                }
            });
        });
    });
}

function run_evaluation(path) {
    console.log(cases_path);
    
    evaluation_cases = [];
    
    n_tp = 0;
    n_fp = 0;
    n_fn = 0;
    
    $.get(path, function(data) {
        lines = data.split("\n");
        for (line of lines) {
            if (line.length > 0) {
                cases = JSON.parse(line);
                evaluation_cases.push(cases);
                
                for (eval_case of cases) {
                    if ("true_entity" in eval_case && "predicted_entity" in eval_case && eval_case.true_entity.entity_id == eval_case.predicted_entity.entity_id) {
                        n_tp += 1;
                    } else {
                        if ("true_entity" in eval_case) {
                            n_fn += 1;
                        }
                        if ("predicted_entity" in eval_case) {
                            n_fp += 1;
                        }
                    }
                }
            }
        }
        precision = n_tp / (n_tp + n_fp);
        recall = n_tp / (n_tp + n_fn);
        f1 = 2 * precision * recall / (precision + recall);
        $("#n_tp").html(n_tp);
        $("#n_fp").html(n_fp);
        $("#n_fn").html(n_fn);
        $("#precision").html((precision * 100).toFixed(2) + " %");
        $("#recall").html((recall * 100).toFixed(2) + " %");
        $("#f_score").html((f1 * 100).toFixed(2) + " %");
        $("#evaluation").show();
        show_article();
    }).fail(function() {
        $("#evaluation").html("ERROR: no file with cases found.");
        show_article();
    });
}

function read_articles_data(path) {
    console.log(path);
    
    articles_data = [];
    
    $.get(path, function(data) {
        lines = data.split("\n");
        for (line of lines) {
            if (line.length > 0) {
                articles_data.push(JSON.parse(line));
            }
        }
    });
}

function read_evaluation() {
    run = $("#evaluation_file").val();

    cases_path = result_files[run] + ".cases";
    run_evaluation(cases_path);
    
    articles_path = result_files[run] + ".jsonl";
    read_articles_data(articles_path);
}
