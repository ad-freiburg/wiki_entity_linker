$("document").ready(function() {
    console.log("document ready");
    benchmarks = ["ours", "conll", "conll-dev", "conll-test", "msnbc", "ace"];
    whitelist = {
        Q18336849: "item with given name property",
        Q27096213: "geographic entity",
        Q483394: "genre",
        Q43229: "organization",
        Q17376908: "languoid",
        Q17537576: "creative work",
        Q2424752: "product",
        Q431289: "brand",
        Q43460564: "chemical entity",
        Q16521: "taxon",
        Q9174: "religion",
        Q7257: "ideology",
        Q4164871: "position",
        Q12737077: "occupation",
        Q216353: "title",
        Q11862829: "academic discipline",
        Q21070598: "narrative entity",
        Q618779: "award",
        Q431289: "brand",
        Q12136: "disease",
        Q4392985: "religious identity",
        Q11514315: "historical period",
        Q1656682: "event",
        Q180684: "conflict",
        Q373899: "record chart",
        Q194465: "annexation",
        Q381072: "crisis",
        Q22222786: "government program",
        Q41710: "ethnic group",
        Q18603729: "dissolution of an administrative territorial entity"
    }
    last_selected_cell = null;

    set_table_head();
    set_table_body();

    // Highlight cells on hover
    $("#benchmarks_table tbody").on("mouseenter", "td", function() {
        // Left-most column and first row should not be hoverable
        var first_cell_text = $(this).closest('tr').find("td:first").text();
        if ($(this).text() != first_cell_text && !first_cell_text.startsWith("total")) {
            $(this).addClass("hovered");
        }
    });

    $("#benchmarks_table tbody").on("mouseleave", "td", function() {
        $(this).removeClass("hovered");
    });

    // Highlight cells on click and un-highlight previously clicked cell
    $("#benchmarks_table tbody").on("click", "td", function() {
        if (last_selected_cell) {
            $(last_selected_cell).removeClass("selected");
        }
        last_selected_cell = null;
        var first_cell_text = $(this).closest('tr').find("td:first").text();
        // Left-most column and first row should not be hoverable
        if ($(this).text() != first_cell_text && !first_cell_text.startsWith("total")) {
            $(this).addClass("selected");
            last_selected_cell = this;
            // Show entity table for selected benchmark and type values
            var first_cell_html = $(this).closest('tr').find("td:first").html();
            var type = first_cell_html.split("<br>")[0].replace(/<\/?b>/g, "");
            var col_index = $(this).parent().children().index($(this)) + 1;
            var benchmark = $("#benchmarks_table thead th:nth-child(" + col_index + ")").text();
            show_entity_table_for_selected_values(benchmark, type);
            // Set selectors to the new values
            $("#benchmark_select").val(benchmark);
            $("#type_select").val(type);
        }
    });
});

function set_table_head() {
    thead = document.getElementById("benchmarks_table_head");
    head_html = "<tr>";
    head_html += "<th></th>";
    for (benchmark of benchmarks) {
        head_html += "<th>" + benchmark + "</th>";
    }
    head_html += "</tr>";
    thead.innerHTML = head_html;
}

function set_table_body() {
    statistics = {};
    benchmarks.forEach(function(benchmark) {
        console.log(benchmark);
        $.get("benchmarks/" + benchmark + ".types.json", function(data) {
            console.log(data);
            statistics[benchmark] = data;
            console.log(statistics);
            console.log(Object.keys(statistics).length);
            if (Object.keys(statistics).length == benchmarks.length) {
                fill_table();
                prepare_selectors();
            }
        });
    });
}

function fill_table() {
    body_html = "<tr>";
    body_html += "<td><b>total</b><br>level 1<br>other</td>";
    for (benchmark of benchmarks) {
        level1 = statistics[benchmark]["total"][0];
        other = statistics[benchmark]["total"][1];
        sum = level1 + other;
        body_html += "<td><b>" + sum + "</b><br>";
        body_html += level1 + " (" + (level1 / sum * 100).toFixed(2) + " %)<br>";
        body_html += other + " (" + (other / sum * 100).toFixed(2) + "%)</td>";
    }
    body_html += "</tr>";
    for (type of Object.keys(statistics[benchmarks[0]].types)) {
        console.log(type);
        body_html += "<tr><td><b>" + type + "</b><br>level 1<br>other" + "</td>";
        for (benchmark of benchmarks) {
            total = statistics[benchmark]["total"][0] + statistics[benchmark]["total"][1];
            level1 = statistics[benchmark].types[type][0];
            other = statistics[benchmark].types[type][1];
            sum = level1 + other;
            sum_percentage = (sum / total * 100).toFixed(2) + "%";
            level1_percentage = (level1 / total * 100).toFixed(2) + "%";
            other_percentage = (other / total * 100).toFixed(2) + "%";
            table_entry = "<b>" + sum + " (" + sum_percentage + ")</b><br>";
            table_entry += level1 + " (" + level1_percentage + ")<br>";
            table_entry += other + " (" + other_percentage + ")<br>";
            body_html += "<td>" + table_entry + "</td>";
        }
        body_html += "</tr>";
    }
    document.getElementById("benchmarks_table_body").innerHTML = body_html;
}

function prepare_selectors() {
    benchmark_select = document.getElementById("benchmark_select");
    for (benchmark of benchmarks) {
        var option = document.createElement("option");
        option.text = benchmark;
        option.value = benchmark;
        benchmark_select.add(option);
    }
    type_select = document.getElementById("type_select");
    for (type of Object.keys(statistics[benchmarks[0]].types)) {
        var option = document.createElement("option");
        option.text = type;
        option.value = type;
        type_select.add(option);
    }
    show_entity_table();
}

function show_entity_table() {
    benchmark = document.getElementById("benchmark_select").value;
    type = document.getElementById("type_select").value;
    show_entity_table_for_selected_values(benchmark, type);

    // Iterate over benchmarks table cells in the first column to find the cell with the corresponding type
    var row_index = null;
    $("#benchmarks_table tbody td:nth-child(1)").each(function(index) {
        var text = $(this).html().split("<br>")[0].replace(/<\/?b>/g, "");
        if (text == type) {
            row_index = index;
        }
    });
    // Iterate over benchmarks table header cells to find the cell with the corresponding benchmark
    var col_index = null;
    $("#benchmarks_table thead th").each(function(index) {
        var text = $(this).text();
        if (text == benchmark) {
            col_index = index;
        }
    });
    // Set corresponding benchmarks table cell to selected and de-select previously selected cell
    var cell = $("#benchmarks_table tbody tr:eq(" + row_index + ") td:eq(" + col_index + ")");
    $(last_selected_cell).removeClass("selected");
    cell.addClass("selected");
    last_selected_cell = cell;
}


function show_entity_table_for_selected_values(benchmark, type) {
    tbody = document.getElementById("entities_table_body");
    tbody.innerHTML = "";
    html_text = "";
    $.get("benchmarks/" + benchmark + ".labels.tsv", function(data) {
        lines = data.split("\n");
        for (let i = 0; i < lines.length; i++) {
            line = lines[i];
            if (line.length > 0) {
                vals = line.split("\t");
                types = vals[3].split(", ");
                is_selected = false;
                type_names = "";
                for (tp of types) {
                    if (whitelist.hasOwnProperty(tp)) {
                        tp = whitelist[tp];
                    }
                    if (type == tp) {
                        is_selected = true;
                    }
                    if (type_names.length > 0) {
                        type_names += ", ";
                    }
                    type_names += tp;
                }
                vals[3] = type_names;
                if (is_selected) {
                    row = "<tr>";
                    for (val of vals) {
                        row += "<td>" + val + "</td>";
                    }
                    row += "</tr>";
                    html_text += row;
                }
            }
        }
        tbody.innerHTML = html_text;
    });
}