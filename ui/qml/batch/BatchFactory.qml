import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
Item {
    id:root
    property var controller
    property int step:0
    property var mappings:[]
    property var variants:({})
    property string batchName:"New Batch"
    property string templateId:""
    property string outputFolder:""
    property var selectedItem:({})
    Timer { interval:900; repeat:true; running:root.step===5; onTriggered:if(root.controller)root.controller.refresh() }
    ColumnLayout { anchors.fill:parent; spacing:Theme.spacing.md
        RowLayout { Layout.fillWidth:true
            Text { text:"Batch Factory"; color:Theme.colors.textPrimary; font.pixelSize:Theme.type.titleLarge; font.weight:Theme.type.semibold }
            Item { Layout.fillWidth:true }
            ComboBox { id:history; Layout.preferredWidth:220; model:root.controller?root.controller.batches:[]; textRole:"name"; valueRole:"id"; onActivated:if(currentValue)root.controller.openBatch(currentValue) }
            Text { text:["Template","Data","Mapping","Variants","Review","Run"][root.step]; color:Theme.colors.textSecondary }
        }
        StackLayout { Layout.fillWidth:true; Layout.fillHeight:true; currentIndex:root.step
            BatchSetup { controller:root.controller; batchName:root.batchName; templateId:root.templateId; outputFolder:root.outputFolder; onNextRequested:{ root.batchName=batchName; root.templateId=templateId; root.outputFolder=outputFolder; root.step=1 } }
            BatchInputTable { controller:root.controller; onNextRequested:root.step=2 }
            BatchMapping { controller:root.controller; templateId:root.templateId; onNextRequested:{ root.mappings=mappings; root.step=3 } }
            BatchVariantPanel { controller:root.controller; onNextRequested:{ root.variants=config; root.step=4 } }
            Item { ColumnLayout { anchors.fill:parent; spacing:Theme.spacing.md
                Text { text:"5. Review"; color:Theme.colors.textPrimary; font.pixelSize:Theme.type.titleMedium; font.weight:Theme.type.semibold }
                Text { text:"Dry Run resolves rows, mappings, languages, voices, reusable Assets and safe output paths without creating projects or rendering."; color:Theme.colors.textSecondary; wrapMode:Text.WordWrap; Layout.fillWidth:true }
                RowLayout { Button { text:"Create Batch"; onClicked:{ var id=controller.createBatch(root.batchName,root.templateId,root.outputFolder,root.mappings,root.variants,{translation_policy:"reviewed_only",collision_policy:"keep_both",performance_profile:"balanced"}); if(id) controller.validateBatch() } }; Button { text:"Validate / Dry Run"; enabled:!!controller.currentBatch.id; onClicked:controller.validateBatch() }; Button { text:"Prepare Queue"; enabled:(controller.dryRunSummary.invalid||0)===0; onClicked:controller.prepareQueue(false) } }
                Text { text: controller.dryRunSummary.total ? (controller.dryRunSummary.total+" outputs · "+controller.dryRunSummary.invalid+" invalid · "+controller.dryRunSummary.warnings+" warnings · approximate storage "+Math.round((controller.dryRunSummary.estimatedBytes||0)/1073741824*10)/10+" GB") : "Create the Batch, then run validation."; color:Theme.colors.textPrimary; wrapMode:Text.WordWrap; Layout.fillWidth:true }
                Button { text:"Start Batch"; enabled:controller.currentBatch.totalItems>0; onClicked:{controller.runBatch();root.step=5} }
                Item { Layout.fillHeight:true }
            } }
            Item {
                ColumnLayout { anchors.fill:parent; spacing:Theme.spacing.sm
                    BatchProgress { Layout.fillWidth:true; Layout.preferredHeight:52; controller:root.controller }
                    SplitView { Layout.fillWidth:true; Layout.fillHeight:true
                        BatchQueue { SplitView.fillWidth:true; controller:root.controller; onItemSelected:root.selectedItem=itemData }
                        ScrollView { SplitView.preferredWidth:330
                            ColumnLayout { width:parent.width; spacing:Theme.spacing.md
                                BatchDetails { Layout.fillWidth:true; Layout.preferredHeight:320; itemData:root.selectedItem; controller:root.controller }
                                BatchErrorPanel { Layout.fillWidth:true; Layout.preferredHeight:180; itemData:root.selectedItem }
                            }
                        }
                    }
                }
            }
        }
    }
}
